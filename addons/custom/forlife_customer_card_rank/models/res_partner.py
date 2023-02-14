# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    card_rank_ids = fields.One2many('partner.card.rank', inverse_name='customer_id', string='Card Rank')
    card_rank_format = fields.Html('Card Rank Format', compute='_compute_card_rank')
    card_rank_tokyolife = fields.Html('Card Rank TokyoLife', compute='_compute_card_rank')

    def _compute_card_rank(self):
        for line in self:
            data = line.card_rank_ids.generate_card_rank_data()
            line.card_rank_format = data.get(f'{self.env.ref("forlife_point_of_sale.brand_format").code}-{str(line.id)}', 'No data')
            line.card_rank_tokyolife = data.get(f'{self.env.ref("forlife_point_of_sale.brand_tokyolife").code}-{str(line.id)}', 'No data')

