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
            if r.store == 'format':
                history_points = r.partner_id.history_points_format_ids
                expired_at = r.partner_id.reset_day_of_point_format
                remaining = r.partner_id.total_points_available_format
            else:
                history_points = r.partner_id.history_points_forlife_ids
                expired_at = r.partner_id.reset_day_of_point_forlife
                remaining = r.partner_id.total_points_available_forlife
            data.append({
                'id': r.partner_id.id,
                'score': {
                    brand.get(r.store): {
                        'used': sum(history_points.mapped('points_used')),
                        'remaining': remaining or 0,
                        'expired_at': expired_at and expired_at.strftime('%Y-%m-%d %H:%M:%S') or None,
                    }
                }
            })
        return data
