# -*- coding: utf-8 -*-
from odoo import api, fields,models,_
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError


class SaleOrderPromotion(models.Model):
    _name = 'sale.order.promotion'

    product_id = fields.Many2one('product.product', string='Product')
    value = fields.Float(string='Value')
    account_id = fields.Many2one('account.account', string="Account")
    description = fields.Char(string="Description")
    order_id = fields.Many2one("sale.order", string="Order")
