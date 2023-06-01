# -*- coding: utf-8 -*-
from odoo import api, fields,models,_
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError

ACCOUNT_DOMAIN = "['&', '&', '&', ('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card')), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"

class ProductCategory(models.Model):
    _inherit = 'product.category'

    promotion_account_id = fields.Many2one("account.account", string="Promotion account", company_dependent=True, domain=ACCOUNT_DOMAIN)
    product_gift_account_id = fields.Many2one("account.account", string="Gift account", company_dependent=True, domain=ACCOUNT_DOMAIN)
    discount_account_id = fields.Many2one("account.account", string="Discount account", company_dependent=True, domain=ACCOUNT_DOMAIN)
    expense_online_account_id = fields.Many2one("account.account", string="Expense online account", company_dependent=True, domain=ACCOUNT_DOMAIN)
    expense_sale_account_id = fields.Many2one("account.account", string="Expense sale account", company_dependent=True, domain=ACCOUNT_DOMAIN)
    income_online_account_id = fields.Many2one("account.account", string="Income online account", company_dependent=True, domain=ACCOUNT_DOMAIN)
    income_sale_account_id = fields.Many2one("account.account", string="Income sale account", company_dependent=True, domain=ACCOUNT_DOMAIN)