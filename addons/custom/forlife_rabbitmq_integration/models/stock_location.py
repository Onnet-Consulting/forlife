# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = ['stock.location', 'sync.info.rabbitmq.create']
    _create_action = 'update'

    @api.model
    def domain_record_sync_info(self):
        return ['|', '&', '&', ('usage', '=', 'internal'), ('warehouse_id.company_id.code', '!=', False), '&',
                ('warehouse_id.company_id.code', '=', '1400'), ('warehouse_id.whs_type.code', 'in', ('3', '4')),
                '&', ('warehouse_id.company_id.code', '!=', '1400'), ('warehouse_id.whs_type.code', 'in', ('1', '2', '5'))]

    def get_sync_info_value(self):
        return [{
            'id': line.warehouse_id.id,
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'storages': [{
                'location_id': location.id,
                'location_code': location.code or '',
                'location_name': location.name or '',
            } for location in line.warehouse_id.view_location_id.child_internal_location_ids],
        } for line in self]
