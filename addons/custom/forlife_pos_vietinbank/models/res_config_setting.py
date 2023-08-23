# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vietinbank_uri = fields.Char(string='Vietinbank Uri', config_parameter='vietinbank.uri')
    vietinbank_client_id = fields.Char(string='Vietinbank Client ID', config_parameter='vietinbank.client.id')
    vietinbank_client_secret = fields.Char(string='Vietinbank Client secret', config_parameter='vietinbank.client.secret')
