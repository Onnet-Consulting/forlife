from odoo import api, fields, models

class ProductCategory(models.Model):
    _inherit = 'product.category'

    asset_group = fields.Boolean('Nhóm tài sản')