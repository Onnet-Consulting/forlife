# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class PromotionRewardLine(models.Model):
    _name = 'promotion.reward.line'
    _description = 'Promotion Reward'
    _order = 'quantity_min'

    program_id = fields.Many2one('promotion.program')
    quantity_min = fields.Float('Minimum Quantity Required')
    reward_type = fields.Selection(related='program_id.reward_type', string='Reward Type')
    quantity = fields.Float('Quantity')
    disc_amount = fields.Float('Discount Amount')
    disc_percent = fields.Float('Discount Percent')
    disc_fixed_price = fields.Float('Discount Fixed Price')
    disc_max_amount = fields.Float('Max Discount Amount')
