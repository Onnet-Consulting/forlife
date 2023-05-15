# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class Store(models.Model):
    _name = 'store'
    _inherit = ['store', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update']
    _create_action = 'update'
    _update_action = 'update'

    def get_sync_create_data(self):
        data = []
        for store in self:
            vals = {
                'id': store.warehouse_id.id,
                'updated_at': store.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'start_date': store.start_date.strftime('%Y-%m-%d') if store.start_date else None,
                'opening_time': {
                    'open': {
                        'hour': int(store.opening_time),
                        'minute': int((store.opening_time - int(store.opening_time)) * 60)
                    },
                    'close': {
                        'hour': int(store.closing_time),
                        'minute': int((store.closing_time - int(store.closing_time)) * 60)
                    }
                },
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['start_date', 'opening_time', 'closing_time']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        data = []
        for store in self:
            vals = {
                'id': store.warehouse_id.id,
                'updated_at': store.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            }
            if 'start_date' in field_update:
                vals.update({
                    'start_date': store.start_date.strftime('%Y-%m-%d') if store.start_date else None,
                })
            if 'opening_time' in field_update or 'closing_time' in field_update:
                vals.update({
                    'opening_time': {
                        'open': {
                            'hour': int(store.opening_time),
                            'minute': int((store.opening_time - int(store.opening_time)) * 60)
                        },
                        'close': {
                            'hour': int(store.closing_time),
                            'minute': int((store.closing_time - int(store.closing_time)) * 60)
                        }
                    },
                })
            data.extend([copy.copy(vals)])
        return data
