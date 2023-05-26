from odoo import api, fields, models
from odoo.tools import float_compare

class ProductProduct(models.Model):
    _inherit = 'product.product'

    combo_id = fields.Many2one('product.combo', related='product_tmpl_id.combo_id', string="Product Combo", store=True)
    attribute_id = fields.Many2one('product.attribute', string="Color Attribute", store=True)

    def write(self, values):
        values['attribute_id'] = int(self.product_template_attribute_value_ids.attribute_id.id) if self.product_template_attribute_value_ids.attribute_id.id else None

        return super().write(values)

    def create(self, vals):
        vals['attribute_id'] = int(self.product_template_attribute_value_ids.attribute_id.id) if self.product_template_attribute_value_ids.attribute_id.id else None

        return super().write(vals)