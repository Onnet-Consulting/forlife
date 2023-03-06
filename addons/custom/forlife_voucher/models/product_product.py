from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    price = fields.Float(string='Price', digits='Product Price')

