# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'sync.info.rabbitmq']

    def action_new_record(self):
        data = []
        brands = self.env['res.brand'].search_read([], ['id', 'code'])
        tokyolife_id = next((x.get('id') for x in brands if x.get('code') == 'TKL'), False)
        format_id = next((x.get('id') for x in brands if x.get('code') == 'FMT'), False)
        for record in self:
            data.append({
                'id': record.id,
                'created_at': record.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': record.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'name': record.name or '',
                'code': record.ref or '',
                'phone_number': record.phone or '',
                'email': record.email or '',
                'birthday': record.birthday and record.birthday.strftime('%Y-%m-%d') or '',
                'score_and_rank': {
                    'tokyolife': {
                        'total': sum([x.points_fl_order + x.points_back for x in record.history_points_forlife_ids]),
                        'used': sum([x.points_used for x in record.history_points_forlife_ids]),
                        'remaining': sum([x.points_store for x in record.history_points_forlife_ids]),
                        'rank': {
                            'id': record.card_rank_by_brand.get(str(tokyolife_id))[0],
                            'name': record.card_rank_by_brand.get(str(tokyolife_id))[1]
                        } if tokyolife_id and record.card_rank_by_brand and record.card_rank_by_brand.get(str(tokyolife_id)) else None
                    },
                    'format': {
                        'total': sum([x.points_fl_order + x.points_back for x in record.history_points_format_ids]),
                        'used': sum([x.points_used for x in record.history_points_format_ids]),
                        'remaining': sum([x.points_store for x in record.history_points_format_ids]),
                        'rank': {
                            'id': record.card_rank_by_brand.get(str(format_id))[0],
                            'name': record.card_rank_by_brand.get(str(format_id))[1]
                        } if format_id and record.card_rank_by_brand and record.card_rank_by_brand.get(str(format_id)) else None
                    }
                }
            })

