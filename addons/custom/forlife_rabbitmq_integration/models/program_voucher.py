# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class ProgramVoucher(models.Model):
    _name = 'program.voucher'
    _inherit = ['program.voucher', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_create_data(self):
        data = []
        for pv in self:
            vals = {
                'id': pv.id,
                'created_at': pv.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': pv.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'start_date': pv.start_date.strftime('%Y-%m-%d %H:%M:%S') if pv.start_date else None,
                'end_date': pv.end_date.strftime('%Y-%m-%d %H:%M:%S') if pv.end_date else None,
                'apply_contemp_time': pv.apply_contemp_time or False,
                'apply_many_times': pv.apply_many_times or False,
                'is_full_price_applies': pv.is_full_price_applies or False,
                'brand_id': pv.brand_id.name or None,
                'name': pv.name or None,
                'using_limit': pv.using_limit or 0,
                'voucher_count': pv.voucher_count or 0,
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['start_date', 'end_date', 'apply_contemp_time', 'apply_many_times',
                              'is_full_price_applies', 'brand_id', 'name', 'using_limit', 'voucher_count']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'apply_contemp_time': 'apply_contemp_time',
            'apply_many_times': 'apply_many_times',
            'is_full_price_applies': 'is_full_price_applies',
            'name': 'name',
            'using_limit': 'using_limit',
            'voucher_count': 'voucher_count',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key)
                })
        data = []
        for pv in self:
            vals.update({
                'id': pv.id,
                'updated_at': pv.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            if 'end_date' in values:
                vals.update({'end_date': pv.end_date.strftime('%Y-%m-%d %H:%M:%S') if pv.end_date else None})
            if 'start_date' in values:
                vals.update({'start_date': pv.start_date.strftime('%Y-%m-%d %H:%M:%S') if pv.start_date else None})
            if 'brand_id' in values:
                vals.update({'brand_id': pv.brand_id.name or None})
            data.extend([copy.copy(vals)])
        return data
