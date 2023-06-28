from odoo import api, fields, models
from odoo.tools import float_compare

class ProductProduct(models.Model):
    _inherit = 'product.product'
    #
    # combo_id = fields.Many2one('product.combo', related='product_tmpl_id.combo_id', string="Product Combo", store=True)
    #
    # def write(self, values):
    #
    # def _ids2str(self, list_ids):
    #     return ','.join([str(i) for i in sorted(list_ids.ids)])
    #
    # def _compute_attribute_ids(self):
    #     for product in self:
    #         product.attribute_ids = self._ids2str(self.product_template_attribute_value_ids.attribute_id)