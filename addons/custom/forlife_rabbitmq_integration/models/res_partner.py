# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    @api.model
    def domain_record_sync_info(self):
        return [('group_id', '=', self.env.ref('forlife_pos_app_member.partner_group_c').id)]

    def get_sync_info_value(self):
        brands = self.env['res.brand'].search_read([], ['id', 'code'])
        tokyolife_id = next((x.get('id') for x in brands if x.get('code') == 'TKL'), False)
        format_id = next((x.get('id') for x in brands if x.get('code') == 'FMT'), False)
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'name': line.name or None,
            'code': line.ref or None,
            'phone_number': line.phone or None,
            'email': line.email or None,
            'birthday': line.birthday and line.birthday.strftime('%Y-%m-%d') or None,
            'address': {
                'city': {
                    'id': line.state_id.id,
                    'name': line.state_id.name,
                } if line.state_id else None,
                'address': line.street or None
            },
            'score': {
                'TKL': {
                    'used': sum([x.points_used for x in line.history_points_forlife_ids]),
                    'remaining': line.total_points_available_forlife or 0,
                    'expired_at': line.reset_day_of_point_forlife and line.reset_day_of_point_forlife.strftime('%Y-%m-%d %H:%M:%S') or None,
                },
                'FMT': {
                    'used': sum([x.points_used for x in line.history_points_format_ids]),
                    'remaining': line.total_points_available_format or 0,
                    'expired_at': line.reset_day_of_point_format and line.reset_day_of_point_format.strftime('%Y-%m-%d %H:%M:%S') or None,
                },
            },
            'rank': {
                'TKL': {
                    'id': line.card_rank_by_brand.get(str(tokyolife_id))[0],
                    'name': line.card_rank_by_brand.get(str(tokyolife_id))[1]
                } if tokyolife_id and line.card_rank_by_brand and line.card_rank_by_brand.get(str(tokyolife_id)) else None,
                'FMT': {
                    'id': line.card_rank_by_brand.get(str(format_id))[0],
                    'name': line.card_rank_by_brand.get(str(format_id))[1]
                } if format_id and line.card_rank_by_brand and line.card_rank_by_brand.get(str(format_id)) else None
            }
        } for line in self]

    @api.model
    def get_field_update(self):
        return ['name', 'phone', 'email', 'birthday', 'state_id', 'street']
