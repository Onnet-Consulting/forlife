# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PartnerCardRankLine(models.Model):
    _name = 'partner.card.rank.line'
    _inherit = ['partner.card.rank.line', 'sync.info.rabbitmq.create']
    _create_action = 'update'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.old_card_rank_id != f.new_card_rank_id)

    def get_sync_info_value(self):
        rec = self.mapped('partner_card_rank_id.customer_id')
        return rec.get_sync_info_value()
