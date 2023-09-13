from odoo import api, fields, models


class AssetLocation(models.Model):
    _name = 'asset.location'
    _description = 'Asset Location'

    code = fields.Char('Code')
    name = fields.Char('Name')
    address = fields.Char("Address")
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]
