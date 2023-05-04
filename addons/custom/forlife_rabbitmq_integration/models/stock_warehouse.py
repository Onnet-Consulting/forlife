# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class StockWarehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ['stock.warehouse', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def domain_record_sync_info(self):
        wh_type = [wht['id'] for wht in self.env['stock.warehouse.type'].search_read([('code', 'in', ('3', '4', '5'))], ['id'])]
        return self.filtered(lambda f: f.whs_type.id in wh_type)

    def get_sync_create_data(self):
        data = []
        for wh in self:
            vals = {
                'id': wh.id,
                'created_at': wh.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': wh.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'name': wh.name or None,
                'name_with_index': wh.short_name_internal or None,
                'code': wh.code or None,
                'status': wh.status_ids.name or None,
                'type': wh.whs_type.code,
                'location': {
                    'longitude': wh.whs_longitude,
                    'latitude': wh.whs_latitude,
                },
                'region': {
                    'id': wh.sale_province_id.id,
                    'name': wh.sale_province_id.name
                } if wh.sale_province_id else None,
                'city': {
                    'id': wh.state_id.id,
                    'name': wh.state_id.name
                } if wh.state_id else None,
                'district': {
                    'id': wh.district_id.id,
                    'name': wh.district_id.name
                } if wh.district_id else None,
                'ward': {
                    'id': wh.ward_id.id,
                    'name': wh.ward_id.name
                } if wh.ward_id else None,
                'address': wh.street or None,
                'phone_number': wh.phone or None,
                'manager': {
                    'id': wh.manager_id.id,
                    'name': wh.manager_id.name or None,
                    'phone_number': wh.manager_id.mobile_phone or None,
                    'email': wh.manager_id.work_email or None,
                } if wh.manager_id else None,
                'storages': [{
                    'location_id': location.id,
                    'location_code': location.code,
                    'location_name': location.name,
                } for location in wh.view_location_id.child_internal_location_ids],
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        if self.domain_record_sync_info():
            return False
        field_check_update = [
            'name', 'short_name_internal', 'code', 'status_ids', 'whs_type', 'whs_longitude', 'whs_latitude',
            'phone', 'sale_province_id', 'state_id', 'district_id', 'ward_id', 'street', 'manager_id'
        ]
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        whs = self.domain_record_sync_info()
        if not whs:
            return False
        map_key_rabbitmq = {
            'name': 'name',
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
        for wh in whs:
            vals.update({
                'id': wh.id,
                'updated_at': wh.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            if 'code' in values:
                vals.update({
                    'code': wh.code or None
                })
            if 'whs_type' in values:
                vals.update({
                    'type': wh.whs_type.code if wh.whs_type else None
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
            data.extend([copy.copy(vals)])
        return data
