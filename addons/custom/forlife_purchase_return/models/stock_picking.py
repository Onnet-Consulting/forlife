import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self._context.get('endloop'):
            return res
        for picking in self:
            if (picking.purchase_id and picking.purchase_id.is_return) or\
                    (picking.move_ids and picking.move_ids[0]._is_purchase_return()):
                picking.create_return_valuation_npl()
        return res

    def create_return_nk_picking(self, po, record, list_line_xk, account_move=None):
        picking_type_in = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', self.env.company.id)], limit=1)
        if po and po.picking_type_id and po.picking_type_id.return_picking_type_id:
            picking_type_id = po.picking_type_id.return_picking_type_id.id
        else:
            picking_type_id = picking_type_in.id

        master_xk = {
            "is_locked": True,
            "immediate_transfer": False,
            'reason_type_id': self.env.ref('forlife_stock.reason_type_7').id,
            'location_id': po.warehouse_material.id if po and po.warehouse_material else self.env.ref('forlife_stock.import_production_order').id,
            'location_dest_id': record.location_id.id,
            'scheduled_date': datetime.datetime.now(),
            'origin': po.name + " nhập trả NPL" if po else record.name + " nhập trả NPL",
            'other_export': True,
            'state': 'assigned',
            'picking_type_id': picking_type_id,
            'move_ids_without_package': list_line_xk,
            'other_import': True
        }
        xk_picking = self.env['stock.picking'].with_context({'skip_immediate': True, 'endloop': True}).create(master_xk)
        xk_picking.button_validate()
        if account_move:
            xk_picking.write({'account_xk_id': account_move.id})
        record.write({'picking_xk_id': xk_picking.id})
        return xk_picking

    def create_return_valuation_npl(self):
        lines_nk = []
        invoice_line_npls = []
        po = self.purchase_id
        npl_location_id = self.env.ref('forlife_stock.import_production_order')
        if self.purchase_id and self.purchase_id.is_return and self.purchase_id.warehouse_material:
            npl_location_id = self.purchase_id.warehouse_material

        for move in self.move_ids:
            production_order = self.env['production.order'].search(
                [('product_id', '=', move.product_id.id), ('type', '=', 'normal')], limit=1)
            if not production_order:
                continue
            if move.product_id.categ_id and move.product_id.categ_id.property_stock_valuation_account_id:
                account_1561 = move.product_id.categ_id.property_stock_valuation_account_id.id
            else:
                raise ValidationError("Danh mục sản phẩm chưa được cấu hình đúng")

            credit = 0
            production_data = []
            for production_line in production_order.order_line_ids:
                product_plan_qty = move.quantity_done / production_order.product_qty * production_line.product_qty
                debit = production_line.price * product_plan_qty

                if not production_line.product_id.product_tmpl_id.x_type_cost_product:
                    lines_nk.append((0, 0, {
                        'product_id': production_line.product_id.id,
                        'product_uom': production_line.uom_id.id,
                        'price_unit': production_line.price,
                        'location_id': npl_location_id.id,
                        'location_dest_id': self.location_id.id,
                        'product_uom_qty': product_plan_qty,
                        'quantity_done': product_plan_qty,
                        'amount_total': production_line.price * product_plan_qty,
                        'reason_type_id': self.env.ref('forlife_stock.reason_type_7').id,
                        'reason_id': npl_location_id.id,
                    }))
                    # Bút toán cho nguyên phụ liệu
                    debit_npl = (0, 0, {
                        'account_id': npl_location_id.valuation_out_account_id.id,
                        'name': production_line.product_id.name,
                        'debit': debit,
                        'credit': 0,
                        # 'is_uncheck': True,
                    })
                    invoice_line_npls.append(debit_npl)
                    credit += debit

            # Bút toán cho nguyên phụ liệu
            if credit > 0:
                credit_npl = (0, 0, {
                    'account_id': account_1561,
                    'name': move.product_id.name,
                    'debit': 0,
                    'credit': credit,
                    # 'is_uncheck': True,

                })
                invoice_line_npls.append(credit_npl)

        if invoice_line_npls and lines_nk:
            account_nl = self.create_account_move(po, invoice_line_npls, self)
            master_xk = self.create_return_nk_picking(po, self, lines_nk, account_nl)
        return True


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        self.ensure_one()
        if self.origin_returned_move_id or not self.purchase_line_id or not self.product_id.id:
            return super(StockMove, self)._get_price_unit()
        if not self.purchase_line_id.order_id.is_return:
            return super(StockMove, self)._get_price_unit()

        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        line = self.purchase_line_id
        order = line.order_id
        price_unit = line.price_unit
        if line.taxes_id:
            qty = line.product_qty or 1
            price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=qty)['total_void']
            price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
        if line.product_uom.id != line.product_id.uom_id.id:
            price_unit *= line.product_uom.factor / line.product_id.uom_id.factor

        if order.currency_id != order.company_id.currency_id:
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self), round=False)

        return price_unit

    def _get_in_svl_vals(self, forced_quantity):
        return_move = self.filtered(lambda m: m.purchase_line_id and m.purchase_line_id.order_id.is_return)
        svl_vals_list = super(StockMove, self - return_move)._get_in_svl_vals(forced_quantity)

        for move in return_move:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = move.product_id.standard_price
            if move.product_id.cost_method != 'standard':
                unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            if move.picking_id.other_import and move.picking_id.location_id.is_price_unit:
                unit_cost = move.amount_total / move.previous_qty if move.previous_qty != 0 else 0
            return_quantity = forced_quantity or valued_quantity
            svl_vals = move.product_id._prepare_in_svl_vals(-return_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return svl_vals_list
