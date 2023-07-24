# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PartnerCardRankLine(models.Model):
    _name = 'partner.history.point'
    _inherit = ['partner.history.point', 'sync.info.rabbitmq.create']
    _create_action = 'update'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.points_used != 0 or f.points_store != 0)

    def get_sync_info_value(self):
        rec = self.mapped('partner_id')
        return rec.get_sync_info_value()
