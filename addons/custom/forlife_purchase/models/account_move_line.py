# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # fields lưu giá trị product chi phí cho hac toán phân bổ chi phí mua hàng
    product_expense_origin_id = fields.Many2one('product.product', string='Product Expense Origin')