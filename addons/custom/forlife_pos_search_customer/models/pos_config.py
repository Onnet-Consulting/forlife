# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, _


class PosConfig(models.Model):
    _inherit = 'pos.config'
    _description = 'Point of Sale Configuration'

    pos_search_customer = fields.Boolean(default=True)
