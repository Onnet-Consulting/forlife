# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PointsPromotion(models.Model):
    _inherit = 'points.promotion'

    card_rank_value_convert = fields.Float('Card Rank Value Convert', default=1000, copy=False)
    card_rank_point_addition = fields.Float('Card Rank Point Addition', default=1, copy=False)
    card_rank_active = fields.Boolean('Active', default=True)
    accumulate_by_rank_ids = fields.One2many('accumulate.by.rank', 'points_promotion_id', 'Accumulate')

    _sql_constraints = [
        ('check_card_rank_value_convert', 'CHECK (card_rank_value_convert > 0)', 'Card Rank Value Convert must be greater than 0'),
        ('check_card_rank_point_addition', 'CHECK (card_rank_point_addition > 0)', 'Card Rank Point Addition must be greater than 0'),
    ]
