# -*- coding: utf-8 -*-
from odoo import api, fields,models,_
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError


class SaleOrderPromotion(models.Model):
    _name = 'sale.order.promotion'
    _description = 'SO promotion'

    product_id = fields.Many2one('product.product', string='Product')
    value = fields.Float(string='Value')
    account_id = fields.Many2one('account.account', string="Account")
    description = fields.Char(string="Description")
    order_id = fields.Many2one("sale.order", string="Order")
    product_uom_qty = fields.Float(string="Quantity", digits='Product Unit of Measure',)
    tax_id = fields.Many2many(comodel_name='account.tax', string="Taxes", context={'active_test': False})
    promotion_type = fields.Selection([
        ('diff_price', 'Làm giá'),
        ('discount', 'Chiết khấu'),
        ('vip_amount_remain', 'Giảm giá trực tiếp'),
        ('vip_amount', 'Hạng thẻ'),
        ('nhanh_shipping_fee', 'Phí vận chuyển'),
        ('customer_shipping_fee', 'Phí ship báo khách hàng'),
        ('reward', 'Chiết khấu tổng đơn'),
        ('out_point', 'Tiêu điểm'),
        ('in_point', 'Tích điểm'),
    ], string='Loại khuyến mại')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic account")
    order_line_id = fields.Many2one("sale.order.line", string="Order line")
