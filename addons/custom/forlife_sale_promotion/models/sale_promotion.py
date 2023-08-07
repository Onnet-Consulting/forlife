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
        ('diff_price', 'diff_price'),
        ('discount', 'discount'),
        ('vip_amount_remain', 'vip_amount_remain'),
        ('vip_amount', 'vip_amount'),
        ('nhanh_shipping_fee', 'nhanh_shipping_fee'),
        ('customer_shipping_fee', 'customer_shipping_fee'),
        ('reward', 'reward')
    ], string='promotion_type')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic account")
