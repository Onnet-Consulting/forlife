# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PromotionPricelistItem(models.Model):
    _name = 'promotion.pricelist.item'
    _inherit = ['promotion.pricelist.item', 'sync.info.rabbitmq.new', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.remove']
    _new_action = 'new_fixed_pricing'
    _update_action = 'update_fixed_pricing'
    _remove_action = 'remove_fixed_pricing'

    def get_sync_new_data(self):
        data = []
        for coupon in self:
            vals = {
                'id': coupon.id,
                'created_at': coupon.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': coupon.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'program_id': coupon.program_id.id or None,
                'active': coupon.active,
                'product_id': coupon.product_id.id or None,
                'fixed_price': coupon.fixed_price or 0,
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['program_id', 'active', 'product_id', 'fixed_price']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        vals = {}
        for field in field_update:
            vals.update({
                field: values.get(field) or None
            })
        data = []
        for coupon in self:
            vals.update({
                'id': coupon.id,
                'updated_at': coupon.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.append(vals)
        return data
