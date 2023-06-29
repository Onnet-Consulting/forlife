# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
import logging

_logger = logging.getLogger(__name__)


class UTMSource(models.Model):
    _inherit = 'utm.source'

    # tuuh
    x_nhanh_id = fields.Boolean('ID Nhanh')
