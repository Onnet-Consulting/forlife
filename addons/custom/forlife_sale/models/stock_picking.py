from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def confirm_from_so(self, condition=None):
        if condition:
            for move in self.move_ids:
                move.check_quantity()
            self.action_confirm()
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
                'product_uom_id': line.product_id.uom_id.id,
                'quantity': line.product_qty,
                'request_code': line.picking_id.name,
                'vendor_price': line.sale_line_id.price_unit,
                'price_unit': line.sale_line_id.price_unit,
                'warehouse': line.location_id.id,
                'tax_ids': [(6, 0, line.sale_line_id.tax_id.ids)],
                'discount': line.sale_line_id.discount,
                'account_analytic_id': line.account_analytic_id.id,
                'work_order': line.sale_line_id.x_manufacture_order_code_id.id,
                'sale_line_ids': [(4, line.sale_line_id.id)]
            }
            invoice_line_ids.append((0, 0, invoice_line))
        vals = {
            'partner_id': self[0].partner_id.id,
            'move_type': 'out_refund',
            'invoice_line_ids': invoice_line_ids,
            'invoice_origin': line.sale_line_id.order_id.name
        }
        invoice_id = self.env['account.move'].create(vals)
        for line in invoice_id.invoice_line_ids:
            if line.product_id:
                line.account_id = line.product_id.product_tmpl_id.categ_id.x_property_account_return_id
        return invoice_id.id

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.picking_type_id.x_is_return:
            for move in self.move_ids:
                account_move = self.env['account.move'].search([('stock_move_id', '=', move.id)])
                account_move_line = account_move.line_ids.filtered(lambda line: line.debit > 0)
                account_id = move.product_id.product_tmpl_id.categ_id.x_property_account_return_id
                if not account_id:
                    raise UserError(_('Bạn chưa cấu hình tài khoản trả hàng trong danh mục sản phẩm của sản phẩm %s') % move.product_id.name)
                account_move_line.account_id = account_id
        if self.state == "done":
            sale_order = self.env['sale.order'].search([('name', '=', self.origin)]).sudo()
            sale_order._create_invoices().action_post()
        return res
