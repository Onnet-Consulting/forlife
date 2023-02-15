# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_rank = fields.Boolean('Is Rank', default=False)

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        self.with_delay().update_partner_card_rank()
        return res

    def update_partner_card_rank(self):
        partner_card_rank = self.partner_id.card_rank_ids.filtered(lambda f: f.brand_id == self.config_id.store_id.brand_id)
        if partner_card_rank:
            self.create_partner_card_rank_detail(partner_card_rank)
        else:
            partner_card_rank = self.create_partner_card_rank()
            self.create_partner_card_rank_detail(partner_card_rank)

    def create_partner_card_rank(self):
        res = self.env['partner.card.rank'].sudo().create({
            'customer_id': self.partner_id.id,
            'brand_id': self.config_id.store_id.brand_id.id,
        })
        return res

    def create_partner_card_rank_detail(self, partner_card_rank):
        self.env['partner.card.rank.line'].sudo().create({
            'partner_card_rank_id': partner_card_rank.id,
            'order_id': self.id,
            'order_date': self.date_order,
            'value_orders': self.amount_total,
            'value_to_upper': self.amount_total,  # fixme thêm logic giá trị xét hạng và hạng mới
            'old_card_rank_id': partner_card_rank.card_rank_id.id,
            'new_card_rank_id': partner_card_rank.card_rank_id.id,
        })
