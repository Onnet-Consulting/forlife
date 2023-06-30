from odoo import api, fields, models
from odoo.tools import float_compare

from odoo import fields, models, api


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    product_id = fields.Many2one('product.product')

class ProductProduct(models.Model):
    _inherit = 'product.product'

    attribute_ids = fields.One2many('product.attribute', 'product_id', string="Related Attributes")
    combo_id = fields.Many2one('product.combo', related='product_tmpl_id.combo_id', string="Product Combo", store=True)