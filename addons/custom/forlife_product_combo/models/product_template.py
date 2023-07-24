from odoo import api, fields, models
from odoo.tools import float_compare

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    combo_id = fields.Many2one('product.combo', string="Product Combo", store=True)
