from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_negative_value = fields.Boolean(string='Giá trị âm')
