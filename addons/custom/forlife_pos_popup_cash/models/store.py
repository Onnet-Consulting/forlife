from odoo import api, fields, models


class Store(models.Model):
    _inherit = 'store'

    account_intermediary_pos = fields.Many2one('account.account', "Account intermediary")