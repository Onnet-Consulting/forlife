# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PromotionCampaign(models.Model):
    _name = 'promotion.campaign'
    _inherit = ['promotion.campaign', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create_campaign'
    _update_action = 'update_campaign'
    _delete_action = 'delete_campaign'

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
                'customer_domain': campaign.customer_domain or None

            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['name', 'state', 'from_date', 'to_date', 'brand_id', 'customer_domain']
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
            if 'brand_id' in values:
                vals.update({
                    'brand_id': campaign.brand_id.code or None,
                    'id': campaign.id,
                    'updated_at': campaign.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                })
            else:
                vals.update({
                    'id': campaign.id,
                    'updated_at': campaign.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                })
            data.append(vals)
        return data
