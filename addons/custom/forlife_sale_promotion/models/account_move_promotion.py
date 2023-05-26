# -*- coding: utf-8 -*-
from odoo import api, fields,models,_
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError


class AccountMovePromotion(models.Model):
    _name = 'account.move.promotion'

    product_id = fields.Many2one('product.product', string='Product')
    value = fields.Float(string='Value')
    account_id = fields.Many2one('account.account', string="Account")
    description = fields.Char(string="Description")
    move_id = fields.Many2one("account.move", string="Order")
