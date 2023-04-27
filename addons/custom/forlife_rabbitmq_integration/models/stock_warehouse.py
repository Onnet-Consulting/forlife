# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ['stock.warehouse', 'sync.info.rabbitmq.update']
    _update_action = 'update_store'

    def check_update_info(self, values):
        if self.env['store'].search_count([('warehouse_id', 'in', self.ids)]) == 0:
            return False
        field_check_update = [
            'short_name_internal', 'code', 'status_ids', 'whs_longitude', 'whs_latitude', 'phone',
            'sale_province_id', 'state_id', 'district_id', 'ward_id', 'street', 'manager_id'
        ]
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        store = self.env['store'].search_read([('warehouse_id', 'in', self.ids)], ['id', 'warehouse_id'])
        store_by_wh_id = {}
        for s in store:
            store_by_wh_id.update({
                s['warehouse_id'][0]: s['id']
            })
        map_key_rabbitmq = {
            'short_name_internal': 'name_with_index',
            'street': 'address',
            'phone': 'phone_number',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        data = []
        whs = self.filtered(lambda w: w.id in list(store_by_wh_id.keys()))
        for wh in whs:
            vals.update({
                'id': store_by_wh_id.get(wh.id),
                'updated_at': wh.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            if 'code' in values:
                vals.update({
                    'code': wh.code or None
                })
            if 'status_ids' in values:
                vals.update({
                    'status': wh.status_ids.name if wh.status_ids else None
                })
            if 'whs_longitude' in values or 'whs_latitude' in values:
                vals.update({
                    'location': {
                        'longitude': wh.whs_longitude,
                        'latitude': wh.whs_latitude,
                    }
                })
            if 'sale_province_id' in values:
                vals.update({
                    'region': {
                        'id': wh.sale_province_id.id,
                        'name': wh.sale_province_id.name
                    } if wh.sale_province_id else None
                })
            if 'state_id' in values:
                vals.update({
                    'city': {
                        'id': wh.state_id.id,
                        'name': wh.state_id.name
                    } if wh.state_id else None
                })
            if 'district_id' in values:
                vals.update({
                    'district': {
                        'id': wh.district_id.id,
                        'name': wh.district_id.name
                    } if wh.district_id else None
                })
            if 'ward_id' in values:
                vals.update({
                    'ward': {
                        'id': wh.ward_id.id,
                        'name': wh.ward_id.name
                    } if wh.ward_id else None
                })
            if 'manager_id' in values:
                vals.update({
                    'manager': {
                        'id': wh.manager_id.id,
                        'name': wh.manager_id.name or None,
                        'phone_number': wh.manager_id.mobile_phone or None,
                        'email': wh.manager_id.work_email or None,
                    } if wh.manager_id else None
                })
            data.append(vals)
        return data
