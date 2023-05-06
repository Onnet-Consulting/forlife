# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PartnerCardRankLine(models.Model):
    _name = 'partner.history.point'
    _inherit = ['partner.history.point', 'sync.info.rabbitmq.create']
    _create_action = 'update'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.points_used != 0 or f.points_store != 0)

    def get_sync_create_data(self):
        data = []
        brand = {
            'format': 'FMT',
            'forlife': 'TKL',
        }
        for r in self:
            history_points = r.partner_id.history_points_format_ids if r.store == 'format' else r.partner_id.history_points_forlife_ids
            data.append({
                'id': r.partner_id.id,
                'score': {
                    brand.get(r.store): {
                        'used': sum(history_points.mapped('points_used')),
                        'remaining': sum(history_points.mapped('points_store')),
                    }
                }
            })
        return data
