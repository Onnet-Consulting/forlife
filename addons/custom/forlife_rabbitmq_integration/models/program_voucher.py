# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ProgramVoucher(models.Model):
    _name = 'program.voucher'
    _inherit = ['program.voucher', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'start_date': line.start_date.strftime('%Y-%m-%d %H:%M:%S') if line.start_date else None,
            'end_date': line.end_date.strftime('%Y-%m-%d %H:%M:%S') if line.end_date else None,
            'apply_contemp_time': line.apply_contemp_time or False,
            'apply_many_times': line.apply_many_times or False,
            'is_full_price_applies': line.is_full_price_applies or False,
            'brand_id': line.brand_id.name or None,
            'name': line.name or None,
            'using_limit': line.using_limit or 0,
            'voucher_count': line.voucher_count or 0,
        } for line in self]

    @api.model
    def get_field_update(self):
        return ['start_date', 'end_date', 'apply_contemp_time', 'apply_many_times',
                'is_full_price_applies', 'brand_id', 'name', 'using_limit', 'voucher_count']
