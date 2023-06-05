# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy
from odoo.tools.safe_eval import safe_eval


class PromotionCampaign(models.Model):
    _name = 'promotion.campaign'
    _inherit = ['promotion.campaign', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_create_data(self):
        data = []
        for campaign in self:
            vals = {
                'id': campaign.id,
                'created_at': campaign.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': campaign.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'name': campaign.name or None,
                'state': campaign.state or None,
                'from_date': campaign.from_date.strftime('%Y-%m-%d %H:%M:%S') or None,
                'to_date': campaign.to_date.strftime('%Y-%m-%d %H:%M:%S') or None,
                'brand_id': campaign.brand_id.code or None,
                'company_id': campaign.company_id.name or None,
                'customer_domain': safe_eval(campaign.customer_domain),
                'store_ids': campaign.store_ids.mapped('warehouse_id').ids,
                'month_ids': campaign.month_ids.mapped('code'),
                'dayofmonth_ids': campaign.dayofmonth_ids.mapped('code'),
                'dayofweek_ids': campaign.dayofweek_ids.mapped('code'),
                'hour_ids': campaign.hour_ids.mapped('code'),
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['name', 'state', 'from_date', 'to_date', 'brand_id', 'customer_domain',
                              'store_ids', 'month_ids', 'dayofmonth_ids', 'dayofweek_ids', 'hour_ids']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'name': 'name',
            'state': 'state',
            'from_date': 'from_date',
            'to_date': 'to_date',
            'customer_domain': 'customer_domain',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        data = []
        for campaign in self:
            vals.update({
                'id': campaign.id,
                'updated_at': campaign.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            if 'brand_id' in values:
                vals.update({
                    'brand_id': campaign.brand_id.code or None,
                })
            if 'store_ids' in values:
                vals.update({
                    'store_ids': campaign.store_ids.mapped('warehouse_id').ids or None,
                })
            if 'month_ids' in values:
                vals.update({
                    'month_ids': campaign.month_ids.mapped('code') or None,
                })
            if 'dayofmonth_ids' in values:
                vals.update({
                    'dayofmonth_ids': campaign.dayofmonth_ids.mapped('code') or None,
                })
            if 'dayofweek_ids' in values:
                vals.update({
                    'dayofweek_ids': campaign.dayofweek_ids.mapped('code') or None,
                })
            if 'hour_ids' in values:
                vals.update({
                    'hour_ids': campaign.hour_ids.mapped('code') or None,
                })
            data.extend([copy.copy(vals)])
        return data
