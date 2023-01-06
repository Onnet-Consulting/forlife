# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PointsProductLine(models.Model):
    _name = 'points.product.line'
    _description = 'Points Product Line'

    points_product_id = fields.Many2one('points.product', string='Products', required=True)
    event_id = fields.Many2one('event', string='Event', ondelete='cascade')
    point_addition = fields.Integer('Point Additions', required=True)

    _sql_constraints = [
        ('data_uniq', 'unique (points_product_id, event_id)', 'Points Product must be unique !')
    ]
