# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create_customer'
    _update_action = 'update_customer'
    _delete_action = 'delete_customer'

    def get_sync_create_data(self):
        records = self.filtered(lambda p: p.group_id == self.env.ref('forlife_pos_app_member.partner_group_c'))
        if not records:
            return False
        data = []
        brands = self.env['res.brand'].search_read([], ['id', 'code'])
        tokyolife_id = next((x.get('id') for x in brands if x.get('code') == 'TKL'), False)
        format_id = next((x.get('id') for x in brands if x.get('code') == 'FMT'), False)
        for record in records:
            data.append({
                'id': record.id,
                'created_at': record.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': record.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'name': record.name or None,
                'code': record.ref or None,
                'phone_number': record.phone or None,
                'email': record.email or None,
                'birthday': record.birthday and record.birthday.strftime('%Y-%m-%d') or None,
                'address': {
                    'city': {
                        'id': record.state_id.id,
                        'name': record.state_id.name,
                    } if record.state_id else None,
                    'address': record.street or None
                },
                'score': {
                    'TKL': {
                        'used': sum([x.points_used for x in record.history_points_forlife_ids]),
                        'remaining': sum([x.points_store for x in record.history_points_forlife_ids])
                    },
                    'FMT': {
                        'used': sum([x.points_used for x in record.history_points_format_ids]),
                        'remaining': sum([x.points_store for x in record.history_points_format_ids])}
                },
                'rank': {
                    'TKL': {
                        'id': record.card_rank_by_brand.get(str(tokyolife_id))[0],
                        'name': record.card_rank_by_brand.get(str(tokyolife_id))[1]
                    } if tokyolife_id and record.card_rank_by_brand and record.card_rank_by_brand.get(str(tokyolife_id)) else None,
                    'FMT': {
                        'id': record.card_rank_by_brand.get(str(format_id))[0],
                        'name': record.card_rank_by_brand.get(str(format_id))[1]
                    } if format_id and record.card_rank_by_brand and record.card_rank_by_brand.get(str(format_id)) else None
                }
            })
        return data

    def check_update_info(self, values):
        records = self.filtered(lambda p: p.group_id == self.env.ref('forlife_pos_app_member.partner_group_c'))
        if not records:
            return False
        field_check_update = ['name', 'phone', 'email', 'birthday', 'state_id', 'street']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'name': 'name',
            'phone': 'phone_number',
            'email': 'email',
            'birthday': 'birthday'
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        if 'state_id' in values:
            city = self.env['res.country.state'].search_read([('id', '=', values.get('state_id'))], ['name'])
            vals['address'] = {
                'city': {
                    'id': city[0].get('id'),
                    'name': city[0].get('name'),
                } if city else None
            }
        if 'street' in values:
            address = vals.get('address') or {}
            address.update({'address': values.get('street') or None})
            vals['address'] = address
        data = []
        records = self.filtered(lambda p: p.group_id == self.env.ref('forlife_pos_app_member.partner_group_c'))
        for partner in records:
            vals.update({
                'id': partner.id,
                'updated_at': partner.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.extend([copy.copy(vals)])
        return data
