# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class Store(models.Model):
    _name = 'store'
    _inherit = ['store', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update']
    _create_action = 'update'
    _update_action = 'update'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.warehouse_id and f.warehouse_id.whs_type.code in ('3', '4', '5'))

    def get_sync_info_value(self):
        return [{
            'id': line.warehouse_id.id,
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'start_date': line.start_date.strftime('%Y-%m-%d') if line.start_date else None,
            'opening_time': {
                'open': {
                    'hour': int(line.opening_time),
                    'minute': int((line.opening_time - int(line.opening_time)) * 60)
                },
                'close': {
                    'hour': int(line.closing_time),
                    'minute': int((line.closing_time - int(line.closing_time)) * 60)
                }
            },
        } for line in self]

    @api.model
    def get_field_update(self):
        return ['start_date', 'opening_time', 'closing_time']
