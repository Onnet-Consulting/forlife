# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PartnerCardRankLine(models.Model):
    _name = 'partner.card.rank.line'
    _inherit = ['partner.card.rank.line', 'sync.info.rabbitmq.create']
    _create_action = 'update'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.old_card_rank_id != f.new_card_rank_id)

    def get_sync_create_data(self):
        data = []
        for r in self:
            data.append({
                'id': r.partner_card_rank_id.customer_id.id,
                'updated_at': r.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'rank': {
                    r.partner_card_rank_id.brand_id.code: {
                        'id': r.new_card_rank_id.id,
                        'name': r.new_card_rank_id.name,
                    }
                }
            })
        return data
