from odoo import fields, api, models, _


class PosConfigInherit(models.Model):
    _inherit = 'pos.config'

    vietinbank_account_no = fields.Char(string='Vietinbank account No.')
    vietinbank_provider = fields.Char(string='Provider')
    vietinbank_virtual_account = fields.Char(string='Virtual account')