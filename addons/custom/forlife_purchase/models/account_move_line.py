# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # fields lưu giá trị product chi phí cho hac toán phân bổ chi phí mua hàng
    product_expense_origin_id = fields.Many2one('product.product', string='Product Expense Origin')

    # Chặn sinh bút toán chênh lệch tỷ giá tự đông
    @api.model
    def _prepare_reconciliation_partials(self, vals_list):
        partials_vals_list, exchange_data = super(AccountMoveLine, self)._prepare_reconciliation_partials(vals_list)
        exchange_data = {}
        return partials_vals_list, exchange_data

    def _prepare_exchange_difference_move_vals(self, amounts_list, company=None, exchange_date=None):
        res = super(AccountMoveLine, self)._prepare_exchange_difference_move_vals(amounts_list, company, exchange_date)
        if res['move_vals'].get('line_ids'):
            res['move_vals']['line_ids'] = []
        return res

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