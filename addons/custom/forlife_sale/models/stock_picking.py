from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def confirm_from_so(self, condition=None):
        if condition:
            self._sanity_check()
            self.move_ids._set_quantities_to_reservation()
            self.with_context(skip_immediate=True).button_validate()
        else:
            self.action_confirm()

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if vals.get('note'):
            account_id = self.env['account.move'].search([('stock_move_id', 'in', self.move_ids.ids)])
            account_id.update({'narration': self.note})
        return res

    def create_invoice_out_refund(self):
        if not self:
            return
        invoice_line_ids = []
        for line in self.move_ids:
            invoice_line = {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'description': line.product_id.default_code,
                'type': line.product_type,
                'quantity_purchased': line.product_uom_qty,
                'exchange_quantity': 1,
                'uom_id': line.product_id.uom_id.id,
                'quantity': line.product_qty,
                'request_code': line.picking_id.name,
                'vendor_price': line.sale_line_id.price_unit,
                'price_unit': line.sale_line_id.price_unit,
                'warehouse': line.location_id.id,
                'taxes_id': line.sale_line_id.tax_id[0].id if line.sale_line_id.tax_id else None,
                'discount_percent': line.sale_line_id.discount,
                'account_analytic_id': line.account_analytic_id.id,
                'work_order': line.sale_line_id.x_manufacture_order_code_id.id,
                'sale_line_ids': [(4, line.sale_line_id.id)]
            }
            invoice_line_ids.append((0, 0, invoice_line))
        vals = {
            'partner_id': self[0].partner_id.id,
            'move_type': 'out_refund',
            'invoice_line_ids': invoice_line_ids,
        }
        invoice_id = self.env['account.move'].create(vals)
        return invoice_id.id