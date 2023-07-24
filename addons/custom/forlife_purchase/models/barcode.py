from odoo import api, fields, models, _


class ForlifeBarcode(models.Model):
    _name = 'forlife.barcode'
    _rec_name = 'country_id'
    _description = 'Forlife Barcode'

    country_id = fields.Many2one('res.country', string="Country")
    barcode = fields.Char(string="Barcode")