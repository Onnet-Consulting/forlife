# -* coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sap_url = fields.Char(string="API URL", config_parameter="sap_url")
    sap_username = fields.Char(string="Username", config_parameter="sap_username")
    sap_password = fields.Char(string="Password", config_parameter="sap_password")
