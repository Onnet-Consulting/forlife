# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PromotionCode(models.Model):
    _name = 'promotion.code'
    _inherit = ['promotion.code', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create_coupon'
    _update_action = 'update_coupon'
    _delete_action = 'delete_coupon'

    def get_sync_create_data(self):
        data = []
        for coupon in self:
            vals = {
                'id': coupon.id,
                'created_at': coupon.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': coupon.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'program_id': coupon.program_id.id or None,
                'name': coupon.name or None,
                'amount': coupon.amount,
                'consumed_amount': coupon.consumed_amount or 0,
                'limit_usage': coupon.limit_usage or False,
                'expiration_date': coupon.expiration_date.strftime('%Y-%m-%d') if coupon.expiration_date else None,
                'remaining_amount': coupon.remaining_amount,
                'reward_program_id': coupon.reward_program_id.id or None,
                'original_program_id': coupon.original_program_id.id or None,
                'original_order_id': coupon.original_order_id.id or None,
                'reward_for_referring': coupon.reward_for_referring or False,
                'referring_date_from': coupon.referring_date_from.strftime('%Y-%m-%d %H:%M:%S') if coupon.referring_date_from else None,
                'referring_date_to': coupon.referring_date_to.strftime('%Y-%m-%d %H:%M:%S') if coupon.referring_date_to else None,
                'original_code_id': coupon.original_code_id.id or None,
                'referred_partner_id': coupon.referred_partner_id.id or None,
                'partner_id': coupon.partner_id.id or None,
                'surprising_reward_line_id': coupon.surprising_reward_line_id.id or None,
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = [
            'program_id', 'name', 'amount', 'consumed_amount', 'limit_usage', 'expiration_date', 'reward_program_id',
            'original_program_id', 'original_order_id', 'reward_for_referring', 'referring_date_from',
            'referring_date_to', 'original_code_id', 'referred_partner_id', 'partner_id', 'surprising_reward_line_id'
        ]
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        vals = {}
        for field in field_update:
            vals.update({
                field: values.get(field) or None
            })
        data = []
        for coupon in self:
            if 'amount' in field_update or 'consumed_amount' in field_update:
                vals.update({
                    'id': coupon.id,
                    'updated_at': coupon.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'remaining_amount': coupon.amount - coupon.consumed_amount,
                })
            else:
                vals.update({
                    'id': coupon.id,
                    'updated_at': coupon.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                })
            data.append(vals)
        return data
