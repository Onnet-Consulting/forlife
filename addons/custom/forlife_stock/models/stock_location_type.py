from odoo import fields, models, api, _


class StockLocationType(models.Model):
    _name = 'stock.location.type'
    _description = 'Stock Location Type'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    description = fields.Char(string="Description")
