# -*- coding: utf-8 -*-
from odoo import api, fields,models,_
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    promotion_account_id = fields.Many2one("account.account", string="Promotion account")
    product_gift_account_id = fields.Many2one("account.account", string="Gift account")
    discount_account_id = fields.Many2one("account.account", string="Discount account")
    expense_online_account_id = fields.Many2one("account.account", string="Expense online account")
    expense_sale_account_id = fields.Many2one("account.account", string="Expense sale account")
    income_online_account_id = fields.Many2one("account.account", string="Income online account")
    income_sale_account_id = fields.Many2one("account.account", string="Income sale account")