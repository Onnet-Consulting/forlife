# -*- coding: utf-8 -*-
from odoo.addons.nhanh_connector.models import constant
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import requests
import logging


class StockLocation(models.Model):
    _inherit = 'stock.location'

    nhanh_id = fields.Integer('Nhanh ID')
