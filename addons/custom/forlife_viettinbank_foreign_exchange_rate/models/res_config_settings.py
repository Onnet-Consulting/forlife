# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vietin_bank_server_private_key = fields.Binary(related='company_id.vietin_bank_server_private_key', readonly=False)
    vietin_bank_exchange_rate_url = fields.Char(related='company_id.vietin_bank_exchange_rate_url', readonly=False)
    vietin_bank_client_id = fields.Char(related='company_id.vietin_bank_client_id', readonly=False)
    vietin_bank_client_secret = fields.Char(related='company_id.vietin_bank_client_secret', readonly=False)
    vietin_bank_provider_id = fields.Char(related='company_id.vietin_bank_provider_id', readonly=False)
    show_vietin_bank_setting = fields.Boolean(related='company_id.show_vietin_bank_setting')
