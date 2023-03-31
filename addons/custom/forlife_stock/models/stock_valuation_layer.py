# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    x_move_date = fields.Datetime('Date Done', related="stock_move_id.date")
