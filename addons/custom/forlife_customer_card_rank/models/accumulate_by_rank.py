# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccumulateByRank(models.Model):
    _name = 'accumulate.by.rank'
    _description = 'Accumulate by rank'
    _rec_name = 'card_rank_id'
    _order = 'points_promotion_id, sequence'

    points_promotion_id = fields.Many2one('points.promotion', 'Points Promotion', required=True)
    card_rank_id = fields.Many2one('card.rank', 'Card Rank', required=True)
    accumulative_rate = fields.Float('Accumulative rate')
    sequence = fields.Integer('Sequence')

    _sql_constraints = [
        ('card_rank_uniq', 'unique(points_promotion_id,card_rank_id)', 'Card rank must be unique !'),
    ]
    