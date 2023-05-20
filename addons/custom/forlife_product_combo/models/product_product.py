from odoo import api, fields, models
from odoo.tools import float_compare

class ProductProduct(models.Model):
    _inherit = 'product.product'

    combo_id = fields.Many2one('product.combo', string="Product Combo", store=True)
