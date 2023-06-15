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
        return self.filtered(lambda f: f.whs_type.code in ('3', '4', '5'))

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'name': line.name or None,
            'name_with_index': line.short_name_internal or None,
            'code': line.code or None,
            'status': line.status_ids.name or None,
            'type': line.whs_type.code,
            'location': {
                'longitude': line.whs_longitude,
                'latitude': line.whs_latitude,
            },
            'region': {
                'id': line.sale_province_id.id,
                'name': line.sale_province_id.name
            } if line.sale_province_id else None,
            'city': {
                'id': line.state_id.id,
                'name': line.state_id.name
            } if line.state_id else None,
            'district': {
                'id': line.district_id.id,
                'name': line.district_id.name
            } if line.district_id else None,
            'ward': {
                'id': line.ward_id.id,
                'name': line.ward_id.name
            } if line.ward_id else None,
            'address': line.street or None,
            'phone_number': line.phone or None,
            'manager': {
                'id': line.manager_id.id,
                'name': line.manager_id.name or None,
                'phone_number': line.manager_id.mobile_phone or None,
                'email': line.manager_id.work_email or None,
            } if line.manager_id else None,
            'storages': [{
                'location_id': location.id,
                'location_code': location.code,
                'location_name': location.name,
            } for location in line.view_location_id.child_internal_location_ids],
        } for line in self]

    def get_field_update(self):
        return [
            'name', 'short_name_internal', 'code', 'status_ids', 'whs_type', 'whs_longitude', 'whs_latitude',
            'phone', 'sale_province_id', 'state_id', 'district_id', 'ward_id', 'street', 'manager_id'
        ]
