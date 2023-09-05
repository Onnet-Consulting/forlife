# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # fields lưu giá trị product chi phí cho hac toán phân bổ chi phí mua hàng
    product_expense_origin_id = fields.Many2one('product.product', string='Product Expense Origin')

    def _get_stock_valuation_layers(self, move):
        """ Chặn tạo bút toán chênh lệch tỷ giá """
        if move.select_type_inv in ('expense', 'labor'):
            return self.env['stock.valuation.layer']
        return super()._get_stock_valuation_layers(move)

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