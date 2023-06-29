from odoo import api, fields, models
from odoo.tools import float_compare

class ProductProduct(models.Model):
    _inherit = 'product.product'

    attribute_ids = fields.One2many('product.attribute', 'category_id', string="Related Attributes")
    combo_id = fields.Many2one('product.combo', related='product_tmpl_id.combo_id', string="Product Combo", store=True)