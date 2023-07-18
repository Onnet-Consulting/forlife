# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    nhanh_id = fields.Integer('Nhanh ID', copy=False)
