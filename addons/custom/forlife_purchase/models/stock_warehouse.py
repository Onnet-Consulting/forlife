# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    whs_type = fields.Many2one('stock.warehouse.type', string='Type')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    whs_latitude = fields.Float('Geo Latitude', digits=(10, 7))
    whs_longitude = fields.Float('Geo Longitude', digits=(10, 7))
    status = fields.Selection([
        ('ready', 'Opening soon'),
        ('open', 'Open'),
        ('close', 'Close'),
    ], string='Status')