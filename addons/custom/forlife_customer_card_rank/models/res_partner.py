# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    card_rank_ids = fields.One2many('partner.card.rank', inverse_name='customer_id', string='Card Rank')
