from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tolerance = fields.Float(string='Dung sai',digits='Product Unit of Measure')
