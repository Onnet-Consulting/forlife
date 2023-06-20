from odoo import models, fields, _, api


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    show_orderline_on_pos = fields.Boolean('Show on POS')


class ProductProduct(models.Model):
    _inherit = "product.product"

    full_attrs_desc = fields.Char(compute='_compute_full_attrs_desc')

    def _compute_full_attrs_desc(self):
        self.full_attrs_desc = ''
        for product in self:
            valid_ptals = product.product_tmpl_id.valid_product_template_attribute_line_ids.filtered(
                lambda att: att.attribute_id.show_orderline_on_pos)
            if valid_ptals:
                product.full_attrs_desc = '-'.join(valid_ptals.value_ids.mapped('name'))
