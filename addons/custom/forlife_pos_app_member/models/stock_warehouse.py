# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    partner_id = fields.Many2one(default=False, readonly=True)
