from odoo import fields, models, api


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    @api.depends('attribute_line_ids.active', 'attribute_line_ids.product_tmpl_id')
    def _compute_products(self):
        if self.env.context.get('import_valid_skip_error', False):
            for pa in self:
                pa.with_context(active_test=False).product_tmpl_ids = False
        else:
            super(ProductAttribute, self)._compute_products()