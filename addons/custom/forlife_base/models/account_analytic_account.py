from odoo import api, fields, models

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    internal_name = fields.Char('Tên nội bộ')
    address = fields.Char('Địa chỉ')