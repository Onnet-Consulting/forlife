from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    number_days_change_refund = fields.Integer('Number days change/refurd')

