# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval


class PromotionCampaign(models.Model):
    _name = 'promotion.campaign'
    _inherit = ['promotion.campaign', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'name': line.name or None,
            'state': line.state or None,
            'from_date': line.from_date.strftime('%Y-%m-%d %H:%M:%S') or None,
            'to_date': line.to_date.strftime('%Y-%m-%d %H:%M:%S') or None,
            'brand_id': line.brand_id.code or None,
            'company_id': line.company_id.name or None,
            'customer_domain': safe_eval(line.customer_domain),
            'store_ids': line.store_ids.mapped('warehouse_id').ids,
            'month_ids': line.month_ids.mapped('code'),
            'dayofmonth_ids': line.dayofmonth_ids.mapped('code'),
            'dayofweek_ids': line.dayofweek_ids.mapped('code'),
            'hour_ids': line.hour_ids.mapped('code'),
        } for line in self]

    def get_field_update(self):
        return ['name', 'state', 'from_date', 'to_date', 'brand_id', 'customer_domain',
                'store_ids', 'month_ids', 'dayofmonth_ids', 'dayofweek_ids', 'hour_ids']
