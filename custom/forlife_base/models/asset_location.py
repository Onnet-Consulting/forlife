from odoo import api, fields, models

class AssetLocation(models.Model):
    _name = 'asset.location'

    _description = 'Asset Location'
    _rec_name = 'location_name'
    location_code = fields.Char('Location Code')
    location_name = fields.Char('Location Name')
    location_address = fields.Char("Location Address")

    _sql_constraints = [
        ('unique_location_code', 'UNIQUE(location_code)', 'Location Code must be unique!')
    ]