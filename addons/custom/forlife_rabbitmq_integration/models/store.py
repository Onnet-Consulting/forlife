# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class Store(models.Model):
    _name = 'store'
    _inherit = ['store', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create_store'
    _update_action = 'update_store'
    _delete_action = 'delete_store'

    def get_sync_create_data(self):
        data = []
        for store in self:
            vals = {
                'id': store.id,
                'created_at': store.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': store.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'name': store.name or None,
                'name_with_index': store.warehouse_id.short_name_internal or None,
                'code': store.code or None,
                'status': store.warehouse_id.status_ids.name or None,
                'location': {
                    'longitude': store.warehouse_id.whs_longitude,
                    'latitude': store.warehouse_id.whs_latitude,
                },
                'region': {
                    'id': store.warehouse_id.sale_province_id.id,
                    'name': store.warehouse_id.sale_province_id.name
                } if store.warehouse_id.sale_province_id else None,
                'city': {
                    'id': store.warehouse_id.state_id.id,
                    'name': store.warehouse_id.state_id.name
                } if store.warehouse_id.state_id else None,
                'district': {
                    'id': store.warehouse_id.district_id.id,
                    'name': store.warehouse_id.district_id.name
                } if store.warehouse_id.district_id else None,
                'ward': {
                    'id': store.warehouse_id.ward_id.id,
                    'name': store.warehouse_id.ward_id.name
                } if store.warehouse_id.ward_id else None,
                'address': store.warehouse_id.street or None,
                'phone_number': store.warehouse_id.phone or None,
                'manager': {
                    'id': store.warehouse_id.manager_id.id,
                    'name': store.warehouse_id.manager_id.name or None,
                    'phone_number': store.warehouse_id.manager_id.mobile_phone or None,
                    'email': store.warehouse_id.manager_id.work_email or None,
                } if store.warehouse_id.manager_id else None,
                'start_date': store.start_date.strftime('%Y-%m-%d') if store.start_date else None,
                'opening_time': {
                    'open': {
                        'hour': int(store.opening_time),
                        'minute': int((store.opening_time - int(store.opening_time)) * 60)
                    },
                    'close': {
                        'hour': int(store.closing_time),
                        'minute': int((store.closing_time - int(store.closing_time)) * 60)
                    }
                },
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['name', 'start_date', 'opening_time', 'closing_time', 'warehouse_id']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'name': 'name',
            'start_date': 'start_date',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        data = []
        for store in self:
            vals.update({
                'id': store.id,
                'updated_at': store.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            if 'opening_time' in values or 'closing_time' in values:
                vals.update({
                    'opening_time': {
                        'open': {
                            'hour': int(store.opening_time),
                            'minute': int((store.opening_time - int(store.opening_time)) * 60)
                        },
                        'close': {
                            'hour': int(store.closing_time),
                            'minute': int((store.closing_time - int(store.closing_time)) * 60)
                        }
                    },
                })
            if 'warehouse_id' in values:
                vals.update({
                    'name_with_index': store.warehouse_id.short_name_internal or None,
                    'code': store.warehouse_id.code or None,
                    'status': store.warehouse_id.status_ids.name or None,
                    'location': {
                        'longitude': store.warehouse_id.whs_longitude,
                        'latitude': store.warehouse_id.whs_latitude,
                    },
                    'region': {
                        'id': store.warehouse_id.sale_province_id.id,
                        'name': store.warehouse_id.sale_province_id.name
                    } if store.warehouse_id.sale_province_id else None,
                    'city': {
                        'id': store.warehouse_id.state_id.id,
                        'name': store.warehouse_id.state_id.name
                    } if store.warehouse_id.state_id else None,
                    'district': {
                        'id': store.warehouse_id.district_id.id,
                        'name': store.warehouse_id.district_id.name
                    } if store.warehouse_id.district_id else None,
                    'ward': {
                        'id': store.warehouse_id.ward_id.id,
                        'name': store.warehouse_id.ward_id.name
                    } if store.warehouse_id.ward_id else None,
                    'address': store.warehouse_id.street or None,
                    'phone_number': store.warehouse_id.phone or None,
                    'manager': {
                        'id': store.warehouse_id.manager_id.id,
                        'name': store.warehouse_id.manager_id.name or None,
                        'phone_number': store.warehouse_id.manager_id.mobile_phone or None,
                        'email': store.warehouse_id.manager_id.work_email or None,
                    } if store.warehouse_id.manager_id else None,
                })
            data.append(vals)
        return data
