from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    number_days_change_refund = fields.Integer('Number days change/refurd')

