# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PartnerCardRankLine(models.Model):
    _name = 'partner.card.rank.line'
    _inherit = ['partner.card.rank.line', 'sync.info.rabbitmq.create']
    _create_action = 'update_customer'

    def get_sync_create_data(self):
        records = self.filtered(lambda f: f.old_card_rank_id != f.new_card_rank_id)
        if not records:
            return True
        data = []
        for r in records:
            data.append({
                'id': r.partner_card_rank_id.customer_id.id,
                'rank': {
                    r.partner_card_rank_id.brand_id.code: {
                        'id': r.new_card_rank_id.id,
                        'name': r.new_card_rank_id.name,
                    }
                }
            })
        return data
