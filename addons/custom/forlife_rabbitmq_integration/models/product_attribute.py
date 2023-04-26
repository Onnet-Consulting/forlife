# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ProductAttribute(models.Model):
    _name = 'product.attribute'
    _inherit = ['product.attribute', 'sync.info.rabbitmq.new', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.remove']
    _new_action = 'new_attribute'
    _update_action = 'update_attribute'
    _remove_action = 'remove_attribute'

    def get_sync_new_data(self):
        data = []
        for attr in self:
            vals = {
                'id': attr.id,
                'created_at': attr.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': attr.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'code': attr.attrs_code or None,
                'name': attr.name or None,
                'values': [{
                    'id': val.id,
                    'name': val.name,
                    'code': val.code,
                } for val in attr.value_ids] if attr.value_ids else None
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['code', 'name', 'value_ids']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'attrs_code': 'code',
            'name': 'name',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        data = []
        for attr in self:
            if 'value_ids' in field_update:
                vals.update({
                    'id': attr.id,
                    'updated_at': attr.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'values': [{
                        'id': val.id,
                        'name': val.name,
                        'code': val.code,
                    } for val in attr.value_ids] if attr.value_ids else None
                })
            else:
                vals.update({
                    'id': attr.id,
                    'updated_at': attr.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                })
            data.append(vals)
        return data
