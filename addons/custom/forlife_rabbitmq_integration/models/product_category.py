# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_create_data(self):
        data = []
        for category in self:
            vals = {
                'id': category.id,
                'created_at': category.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': category.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'code': category.category_code or None,
                'name': category.name or None,
                'complete_name': category.complete_name or None,
                'parent_id': category.parent_id.id or None,
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['category_code', 'complete_name', 'name', 'parent_id']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'category_code': 'code',
            'complete_name': 'complete_name',
            'name': 'name',
            'parent_id': 'parent_id',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        data = []
        for category in self:
            vals.update({
                'id': category.id,
                'updated_at': category.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.extend([copy.copy(vals)])
        return data
