# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    whs_code = fields.Char(string='Whs Code')
    whs_type = fields.Many2one('stock.warehouse.type', string='Type')
    phone = fields.Char(string="Phone")
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    whs_location = fields.Selection([
        ('s1', 'S1'),
        ('s2', 'S2'),
        ('s3', 'S3'),
        ('s4', 'S4'),
    ], string='Location')
    whs_latitude = fields.Float('Geo Latitude', digits=(10, 7))
    whs_longitude = fields.Float('Geo Longitude', digits=(10, 7))
    status = fields.Selection([
        ('ready', 'Opening soon'),
        ('open', 'Open'),
        ('close', 'Close'),
    ], string='Status')

    note = fields.Text(string='Note')



class StockWarehouseType(models.Model):
    _name = 'stock.warehouse.type'
    _description = "Type of Warehouse"

    name = fields.Char(string='Name')
    code = fields.Char(string='code')