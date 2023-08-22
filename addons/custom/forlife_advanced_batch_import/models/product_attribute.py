from odoo import fields, models, api


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    @api.depends('attribute_line_ids.active', 'attribute_line_ids.product_tmpl_id')
    def _compute_products(self):
        for pa in self:
            pa.with_context(active_test=False).product_tmpl_ids = False
