from odoo import api, fields, models

class AccountTax(models.Model):
    _inherit = 'account.tax'

    code = fields.Char(string='Code')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]