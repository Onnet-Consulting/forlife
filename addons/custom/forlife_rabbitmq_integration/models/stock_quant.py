# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class StockQuant(models.Model):
    _name = 'stock.quant'
    _inherit = ['stock.quant', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update']
    _create_action = 'update'
    _update_action = 'update'

    def check_create_info(self, res):
        stores = self.env['store'].search([('warehouse_id', 'in', res.mapped('warehouse_id').ids)])
        return res.filtered(lambda f: f.location_id.warehouse_id.id in stores.mapped('warehouse_id').ids)

    def get_sync_create_data(self):
        stores = self.env['store'].search([('warehouse_id', 'in', self.mapped('warehouse_id').ids)])
        data = []
        for sqt in self:
            store_id = stores.filtered(lambda f: f.warehouse_id == sqt.location_id.warehouse_id)
            if store_id:
                vals = {
                    'store_id': store_id[0].id,
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
        check_sqt_in_store = self.check_create_info(self)
        field_check_update = ['quantity', 'reserved_quantity']
        return [item for item in field_check_update if item in values] if check_sqt_in_store else False

    def get_sync_update_data(self, field_update, values):
        res = self.check_create_info(self)
        stores = self.env['store'].search([('warehouse_id', 'in', self.mapped('warehouse_id').ids)])
        data = []
        for sqt in res:
            store_id = stores.filtered(lambda f: f.warehouse_id == sqt.location_id.warehouse_id)
            vals = {
                'store_id': store_id[0].id,
                'location_id': sqt.location_id.id,
                'sku': sqt.product_id.default_code or None,
                'remain': sqt.quantity,
                'available': sqt.available_quantity,
                'holding': sqt.reserved_quantity,
                'product_id': sqt.product_id.id,
            }
            data.extend([copy.copy(vals)])
        return data
