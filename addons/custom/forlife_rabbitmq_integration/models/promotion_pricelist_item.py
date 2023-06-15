# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class PromotionPricelistItem(models.Model):
    _name = 'promotion.pricelist.item'
    _inherit = ['promotion.pricelist.item', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'program_id': line.program_id.id or None,
            'active': line.active,
            'product_id': line.product_id.id or None,
            'fixed_price': line.fixed_price or 0,
        } for line in self]

    def get_field_update(self):
        return ['program_id', 'active', 'product_id', 'fixed_price']
