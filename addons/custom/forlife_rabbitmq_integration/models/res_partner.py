# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


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
        self.push_message_to_rabbitmq(data, 'new_customer')

    def check_update_info(self, values):
        field_check_update = ['name', 'ref', 'phone', 'email', 'birthday', 'state_id', 'street']
        return [item for item in field_check_update if item in values]

    def action_update_record(self, field_update, values):
        map_key_rabbitmq = {
            'name': 'name',
            'ref': 'code',
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
        for partner in self:
            vals.update({
                'id': partner.id,
                'updated_at': partner.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.append(vals)
        self.push_message_to_rabbitmq(data, 'update_customer')

    def action_delete_record(self, record_ids):
        data = [{'id': res_id} for res_id in record_ids]
        self.push_message_to_rabbitmq(data, 'remove_customer')
