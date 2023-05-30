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

    def create_return_xk_picking(self, po, record, list_line_xk, account_move=None):
        picking_type_in = self.env['stock.picking.type'].search([
            ('code', '=', 'ingoing'),
            ('company_id', '=', company_id)], limit=1)
        master_xk = {
            "is_locked": True,
            "immediate_transfer": False,
            'reason_type_id': self.env.ref('forlife_stock.reason_type_7').id,
            'location_id': self.env.ref('forlife_stock.import_production_order').id,
            'location_dest_id': record.location_id.id,
            'scheduled_date': datetime.datetime.now(),
            'origin': po.name,
            'other_export': True,
            'state': 'assigned',
            'picking_type_id': picking_type_in.id,
            'move_ids_without_package': list_line_xk
        }
        xk_picking = self.env['stock.picking'].with_context({'skip_immediate': True, 'endloop': True}).create(master_xk)
        xk_picking.button_validate()
        if account_move:
            xk_picking.write({'account_xk_id': account_move.id})
        record.write({'picking_xk_id': xk_picking.id})
        return xk_picking

    def create_return_valuation_npl(self):
        lines_xk = []
        invoice_line_npls = []

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
                    lines_xk.append((0, 0, {
                        'product_id': production_line.product_id.id,
                        'product_uom': production_line.uom_id.id,
                        'price_unit': production_line.price,
                        'location_id': self.env.ref('forlife_stock.import_production_order').id,
                        'location_dest_id': self.location_id.id,
                        'product_uom_qty': product_plan_qty,
                        'quantity_done': product_plan_qty,
                        'amount_total': production_line.price * product_plan_qty,
                        'reason_type_id': self.env.ref('forlife_stock.reason_type_7').id,
                        'reason_id': self.env.ref('forlife_stock.import_production_order').id,
                    }))
                    # Bút toán cho nguyên phụ liệu
                    debit_npl = (0, 0, {
                        'account_id': self.env.ref(
                            'forlife_stock.import_production_order').valuation_out_account_id.id,
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

        if invoice_line_npls and lines_xk:
            account_nl = self.create_account_move(self.purchase_id, invoice_line_npls, self)
            master_xk = self.create_return_xk_picking(self.purchase_id, self, lines_xk, account_nl)
        return True
