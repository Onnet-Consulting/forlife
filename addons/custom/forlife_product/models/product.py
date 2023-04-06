from odoo import api, fields, models

class Product(models.Model):
    _inherit = 'product.template'

    tolerance = fields.Float('Tolerance')
    tolerance_ids = fields.One2many('product.tolerance.line', 'product_id', string='Supplier Tolerance')