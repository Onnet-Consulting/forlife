# -*- coding: utf-8 -*-
from odoo import api, fields,models,_
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError


class AccountMovePromotion(models.Model):
    _name = 'account.move.promotion'
    _description = 'Account Move promotion'

    product_id = fields.Many2one('product.product', string='Product')
    value = fields.Float(string='Value')
    promotion_type = fields.Selection([
        ('diff_price', 'diff_price'),
        ('discount', 'discount'),
        ('vip_amount_remain', 'vip_amount_remain'),
        ('vip_amount', 'vip_amount'),
        ('nhanh_shipping_fee', 'nhanh_shipping_fee'),
        ('customer_shipping_fee', 'customer_shipping_fee'),
        ('reward', 'reward')
    ], string='promotion_type')
    account_id = fields.Many2one('account.account', string="Account")
    description = fields.Char(string="Description")
    move_id = fields.Many2one("account.move", string="Order")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic account")
    partner_id = fields.Many2one('res.partner', required=False)
    tax_id = fields.Many2many(comodel_name='account.tax', string="Taxes", context={'active_test': False})