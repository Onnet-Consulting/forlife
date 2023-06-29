import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
import logging
_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    other_picking_type_id = fields.Many2one('stock.picking.type', string="Kiểu giao nhận xuất/nhập khác")
    other_location_id = fields.Many2one('stock.location', string="Lý do xuất/nhập khác mặc định")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_return_po = fields.Boolean(default=False)

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self._context.get('endloop'):
            return res
        for picking in self:
            if (picking.purchase_id and picking.purchase_id.is_return) or\
                    (picking.move_ids and picking.move_ids[0]._is_purchase_return()):
                picking.create_return_valuation_npl()
        return res

    def _get_picking_info_return(self, po):
        incoming_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', self.env.company.id)], limit=1)
        picking_type_id = incoming_type_id
        if po and po.picking_type_id:
            # if not po.picking_type_id.other_picking_type_id:
            #     raise ValidationError("Vui lòng thiết lập 'Kiểu giao nhận xuất/nhập khác' tại Kiểu giao nhận tương ứng.")
            if po.picking_type_id.other_picking_type_id:
                picking_type_id = po.picking_type_id.other_picking_type_id
            elif po.picking_type_id.return_picking_type_id:
                picking_type_id = po.picking_type_id.return_picking_type_id

        production_order = self.env['production.order'].search([('product_id', 'in', self.move_ids.product_id.ids), ('type', '=', 'normal')], limit=1)
        if (po and po.is_return and po.order_line_production_order) or (po and production_order):
            location_id = self.env['stock.location'].search([('code', '=', 'N0701'), ('company_id', '=', self.env.company.id)], limit=1)
            if not location_id:
                raise ValidationError("Hiện tại sản phẩm xuất trả có sản phẩm đính kèm NPL. Nhưng trong cấu hình Lý Do Nhập Khác chưa định nghĩa loại lý do có Mã = N0701. Yêu cầu liên hệ admin để xử lý")
        elif picking_type_id.other_location_id:
            location_id = picking_type_id.other_location_id
        else:
            location_id = self.env.ref('forlife_stock.import_production_order')

        return picking_type_id, location_id

    def create_return_picking_npl(self, po, record, lines_npl):
        picking_type_id, location_id = self._get_picking_info_return(po)

        vals = {
            "is_locked": True,
            "immediate_transfer": False,
            'reason_type_id': self.env.ref('forlife_stock.reason_type_7').id,
            'location_id': location_id.id,
            'location_dest_id': record.location_id.id,
            'scheduled_date': datetime.datetime.now(),
            'origin': po.name + " nhập trả NPL" if po else record.name + " nhập trả NPL",
            'state': 'assigned',
            'picking_type_id': picking_type_id.id,
            'move_ids_without_package': lines_npl,
            'other_import': True
        }
        picking_npl = self.env['stock.picking'].with_context({'skip_immediate': True, 'endloop': True}).create(vals)
        ctx = picking_npl._context.copy()
        ctx.update({'extend_account_npl': True})
        picking_npl.with_context(ctx).button_validate()
        record.write({'picking_xk_id': picking_npl.id})
        return picking_npl

    def create_return_valuation_npl(self):
        lines_npl = []
        invoice_line_npls = []

        picking_type_id, npl_location_id = self._get_picking_info_return(self.purchase_id)

        for move in self.move_ids:
            production_order = self.env['production.order'].search(
                [('product_id', '=', move.product_id.id), ('type', '=', 'normal')], limit=1)
            if not production_order:
                continue
            if move.product_id.categ_id and move.product_id.categ_id.property_stock_valuation_account_id:
                account_1561 = move.product_id.categ_id.property_stock_valuation_account_id.id
            else:
                raise ValidationError("Danh mục sản phẩm chưa được cấu hình đúng")

            production_data = []
            for production_line in production_order.order_line_ids:
                product_plan_qty = move.quantity_done / production_order.product_qty * production_line.product_qty

                if not production_line.product_id.product_tmpl_id.x_type_cost_product:
                    lines_npl.append((0, 0, {
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
                        'include_move_id': move.id
                    }))

        if lines_npl:
            picking_npl = self.create_return_picking_npl(self.purchase_id, self, lines_npl)
        return True


class StockMove(models.Model):
    _inherit = 'stock.move'

    include_move_id = fields.Many2one('stock.move')

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

    def _account_entry_move(self, qty, description, svl_id, cost):
        am_vals = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        if 'extend_account_npl' in self._context and self.include_move_id and len(am_vals) == 1:
            include_move_id = self.include_move_id
            account_1561 = include_move_id.product_id.categ_id.property_stock_valuation_account_id.id
            if self.reason_id.type_other == 'incoming':
                debit_account_id = self.reason_id.x_property_valuation_out_account_id.id
                credit_account_id = account_1561

                svl = self.env['stock.valuation.layer'].browse(svl_id)
                line_ids = am_vals[0].get('line_ids')

                # FIXME: find true logic
                credit = None
                debit = None
                if len(line_ids) == 2:
                    for line in line_ids:
                        if line[2]['balance'] <= 0:
                            credit = -line[2]['balance']
                        if line[2]['balance'] >= 0:
                            debit = line[2]['balance']

                if credit == None or debit == None:
                    value = self._get_price_unit() * self.quantity_done
                    credit = value
                    debit = value

                # Other debit line account
                line_ids += [(0, 0, {
                    'account_id': debit_account_id,
                    'name': self.product_id.name,
                    'debit': debit,
                    'credit': 0,
                })]
                # Other credit line account
                line_ids += [(0, 0, {
                    'account_id': credit_account_id,
                    'name': include_move_id.product_id.name,
                    'debit': 0,
                    'credit': credit,
                })]
                am_vals[0]['line_ids'] = line_ids

        return am_vals
