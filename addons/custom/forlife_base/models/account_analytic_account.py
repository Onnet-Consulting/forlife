from odoo import api, fields, models

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    code = fields.Char('Code')
    internal_name = fields.Char('Tên nội bộ')
    address = fields.Char('Địa chỉ')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]