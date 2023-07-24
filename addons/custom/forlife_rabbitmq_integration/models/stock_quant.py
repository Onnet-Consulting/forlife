# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class StockQuant(models.Model):
    _name = 'stock.quant'
    _inherit = ['stock.quant', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update']
    _create_action = 'update'
    _update_action = 'update'
    _priority = 1

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.location_id.warehouse_id.whs_type.code in ('3', '4', '5'))

    def get_sync_info_value(self):
        return {
            'updated_at': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': [{
                'store_id': line.location_id.warehouse_id.id,
                'location_id': line.location_id.id,
                'location_code': line.location_id.code or '',
                'sku': line.product_id.default_code or None,
                'remain': line.quantity,
                'available': line.available_quantity,
                'holding': line.reserved_quantity,
                'product_id': line.product_id.id,
            } for line in self]
        }

    def check_update_info(self, list_field, values):
        if 'reserved_quantity' in values and len(values) == 1 and values.get('reserved_quantity', 0) == 0:
            return False
        return super().check_update_info(list_field, values)

    @api.model
    def get_field_update(self):
        return ['quantity', 'reserved_quantity']

    @api.model
    def prepare_message(self, action, target, val):
        val = dict(val)
        val.update({
            'action': action,
            'target': target,
        })
        return val
