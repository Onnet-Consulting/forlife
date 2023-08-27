# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # fields lưu giá trị product chi phí cho hac toán phân bổ chi phí mua hàng
    product_expense_origin_id = fields.Many2one('product.product', string='Product Expense Origin')

    def unlink(self):
        for invoice_line_id in self.filtered(lambda x: x.stock_move_id):
            qty_invoiced = invoice_line_id.stock_move_id.qty_invoiced - invoice_line_id.quantity
            if qty_invoiced <= 0:
                qty_invoiced = 0
            invoice_line_id.stock_move_id.write({
                'qty_invoiced': qty_invoiced,
                'qty_to_invoice': 0,
                'qty_refunded': 0,
            })
        return super(AccountMoveLine, self).unlink()