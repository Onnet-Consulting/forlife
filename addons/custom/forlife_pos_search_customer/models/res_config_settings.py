# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_search_customer = fields.Boolean(related='pos_config_id.pos_search_customer', readonly=False)
