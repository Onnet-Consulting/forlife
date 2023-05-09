# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = ['stock.location', 'sync.info.rabbitmq.create']
    _create_action = 'update'

    def domain_record_sync_info(self):
        return self.filtered(lambda l: l.usage == 'internal' and l.warehouse_id.whs_type.code in ('3', '4', '5'))

    def get_sync_create_data(self):
        data = []
        for location in self:
            vals = {
                'id': location.warehouse_id.id,
                'updated_at': location.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'storages': [{
                    'location_id': location.id,
                    'location_code': location.code,
                    'location_name': location.name,
                } for location in location.warehouse_id.view_location_id.child_internal_location_ids],
            }
            data.append(vals)
        return data
