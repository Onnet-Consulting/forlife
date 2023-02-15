from odoo import api, fields, models

class PointPromotion(models.Model):
    _inherit = 'points.promotion'

    approve_consumption_point = fields.Boolean('Approve Consumption Points')
    apply_all = fields.Boolean('Apply All')

    point_consumption_ids = fields.Many2many('product.product', 'point_promotion_id', string='Consumption Product')