# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class StockQuant(models.Model):
    _name = 'stock.quant'
    _inherit = ['stock.quant', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update']
    _create_action = 'update'
    _update_action = 'update'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.location_id.warehouse_id.whs_type.code in ('3', '4', '5'))

    def get_sync_create_data(self):
        data = []
        for sqt in self:
            vals = {
                'store_id': sqt.location_id.warehouse_id.id,
                'location_id': sqt.location_id.id,
                'sku': sqt.product_id.default_code or None,
                'remain': sqt.quantity,
                'available': sqt.available_quantity,
                'holding': sqt.reserved_quantity,
                'product_id': sqt.product_id.id,
            }
            data.append(vals)
        if data:
            data = {
                'updated_at': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'store_data': data,
            }
        return data

    def check_update_info(self, values):
        if 'reserved_quantity' in values and len(values) == 1 and values.get('reserved_quantity', 0) == 0:
            return False
        check_sqt_sync = self.domain_record_sync_info()
        field_check_update = ['quantity', 'reserved_quantity']
        return [item for item in field_check_update if item in values] if check_sqt_sync else False

    def get_sync_update_data(self, field_update, values):
        res = self.domain_record_sync_info()
        data = []
        for sqt in res:
            vals = {
                'store_id': sqt.location_id.warehouse_id.id,
                'location_id': sqt.location_id.id,
                'sku': sqt.product_id.default_code or None,
                'remain': sqt.quantity,
                'available': sqt.available_quantity,
                'holding': sqt.reserved_quantity,
                'product_id': sqt.product_id.id,
            }
            data.extend([copy.copy(vals)])
        if data:
            data = {
                'updated_at': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'store_data': data,
            }
        return data
