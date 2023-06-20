from odoo import models, fields, _, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    full_attrs_desc = fields.Char(compute='_compute_full_attrs_desc')

    def _compute_full_attrs_desc(self):
        self.full_attrs_desc = ''
        for product in self:
            valid_ptals = product.product_tmpl_id.valid_product_template_attribute_line_ids
            if valid_ptals:
                product.full_attrs_desc = '-'.join(valid_ptals.value_ids.mapped('name'))