# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ProductAttribute(models.Model):
    _name = 'product.attribute'
    _inherit = ['product.attribute', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'code': line.attrs_code or None,
            'name': line.name or None,
            'values': [{
                'id': val.id,
                'name': val.name,
                'code': val.code,
            } for val in line.value_ids] if line.value_ids else None
        } for line in self]

    def get_field_update(self):
        return ['attrs_code', 'name', 'value_ids']
