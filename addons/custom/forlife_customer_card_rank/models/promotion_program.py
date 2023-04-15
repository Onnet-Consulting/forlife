# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PromotionProgram(models.Model):
    _inherit = 'promotion.program'

    skip_card_rank = fields.Boolean('Skip card rank', default=False)
