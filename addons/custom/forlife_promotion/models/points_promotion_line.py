from odoo import api, fields, models, _


class PointsPromotionLine(models.Model):
    _name = 'points.promotion.line'
    _description = 'Points Promotion Line'

    points_promotion_id = fields.Many2one('points.promotion', string='Points Promotion', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Products', required=True)
    point_addition = fields.Integer('Point Addition', required=True)
    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
