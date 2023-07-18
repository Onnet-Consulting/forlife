# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'code': line.category_code or None,
            'name': line.name or None,
            'complete_name': line.complete_name or None,
            'parent_id': line.parent_id.id or None,
            'level': line.level or None,
        } for line in self]

    def get_field_update(self):
        return ['category_code', 'complete_name', 'name', 'parent_id', 'level']
