from odoo import api, fields, models
from odoo.tools import float_compare

class ProductProduct(models.Model):
    _inherit = 'product.product'

    combo_id = fields.Many2one('product.combo', related='product_tmpl_id.combo_id', string="Product Combo", store=True)
    attribute_id = fields.Many2one('product.attribute', string="Color Attribute", store=True)

    def write(self, values):
        if self.attribute_id != None or self.attribute_id != self.product_template_attribute_value_ids.attribute_id.id:
            values['attribute_id'] = self.product_template_attribute_value_ids.attribute_id.id if self.product_template_attribute_value_ids.attribute_id.id else None

        return super().write(values)

    def create(self, vals):
        if self.attribute_id != None or self.attribute_id != self.product_template_attribute_value_ids.attribute_id.id:
            vals['attribute_id'] = self.product_template_attribute_value_ids.attribute_id.id if self.product_template_attribute_value_ids.attribute_id.id else None

        return super().write(vals)