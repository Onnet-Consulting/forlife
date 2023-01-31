from odoo import api, fields, models

class PointsConsumptionLine(models.Model):
    _name = 'points.consumption.line'

    point_promotion_id = fields.Many2one('points.promotion')

    product_id = fields.Many2one('product.product', 'Product')