# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockQuant(models.Model):
    _name = 'stock.quant'
    _inherit = ['stock.quant', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update']
    _create_action = 'update'
    _update_action = 'update'

    def get_sync_create_data(self):
        stores = self.env['store'].search([('warehouse_id', 'in', self.mapped('warehouse_id').ids)])
        data = []
        for sqt in self:
            store_id = stores.filtered(lambda f: f.warehouse_id == sqt.warehouse_id)
            if store_id:
                vals = {
                    'store_id': store_id[0].id,
                    'location_id': sqt.location_id,
                    'sku': sqt.product_id.default_code or None,
                    'remain': sqt.quantity or None,
                    'available': sqt.available_quantity or None,
                    'holding': sqt.reserved_quantity or None,
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
        field_check_update = ['quantity', 'reserved_quantity']
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
