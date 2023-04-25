from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    code = fields.Char(string='Code')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code, company_id)', 'Code must be unique per company!')
    ]
