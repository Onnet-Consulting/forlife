# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PromotionCode(models.Model):
    _name = 'promotion.code'
    _inherit = ['promotion.code', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'program_id': line.program_id.id or None,
            'name': line.name or None,
            'amount': line.amount,
            'consumed_amount': line.consumed_amount or 0,
            'limit_usage': line.limit_usage or False,
            'expiration_date': line.expiration_date.strftime('%Y-%m-%d') if line.expiration_date else None,
            'remaining_amount': line.remaining_amount,
            'reward_program_id': line.reward_program_id.id or None,
            'original_program_id': line.original_program_id.id or None,
            'original_order_id': line.original_order_id.id or None,
            'reward_for_referring': line.reward_for_referring or False,
            'referring_date_from': line.referring_date_from.strftime('%Y-%m-%d %H:%M:%S') if line.referring_date_from else None,
            'referring_date_to': line.referring_date_to.strftime('%Y-%m-%d %H:%M:%S') if line.referring_date_to else None,
            'original_code_id': line.original_code_id.id or None,
            'referred_partner_id': line.referred_partner_id.id or None,
            'partner_id': line.partner_id.id or None,
            'surprising_reward_line_id': line.surprising_reward_line_id.id or None,
        } for line in self]

    @api.model
    def get_field_update(self):
        return [
            'program_id', 'name', 'amount', 'consumed_amount', 'limit_usage', 'expiration_date', 'reward_program_id',
            'original_program_id', 'original_order_id', 'reward_for_referring', 'referring_date_from',
            'referring_date_to', 'original_code_id', 'referred_partner_id', 'partner_id', 'surprising_reward_line_id'
        ]
