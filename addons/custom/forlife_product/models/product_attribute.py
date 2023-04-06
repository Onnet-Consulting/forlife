from odoo import api, fields, models


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    attrs_code = fields.Char('Mã thuộc tính', required=True)

    _sql_constraints = [
        ('unique_attrs_code', 'UNIQUE(attrs_code)', 'Mã thuộc tính phải là duy nhất!')
    ]