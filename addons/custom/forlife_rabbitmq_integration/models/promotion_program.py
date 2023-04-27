# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PromotionProgram(models.Model):
    _name = 'promotion.program'
    _inherit = ['promotion.program', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create_program'
    _update_action = 'update_program'
    _delete_action = 'delete_program'

    def get_sync_create_data(self):
        data = []
        for program in self:
            vals = {
                'id': program.id,
                'created_at': program.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': program.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'campaign_id': program.campaign_id.id or None,
                'active': program.active or False,
                'max_usage': program.max_usage or 0,
                'limit_usage_per_order': program.limit_usage_per_order or False,
                'limit_usage_per_customer': program.limit_usage_per_customer or False,
                'registering_tax': program.registering_tax or False,
                'incl_reward_in_order': program.incl_reward_in_order or False,
                'voucher_program_id': program.voucher_program_id.id or False,
                'voucher_product_variant_id': program.voucher_product_variant_id.id or False,
                'skip_card_rank': program.skip_card_rank or False,
                'limit_usage': program.limit_usage or False,
                'with_code': program.with_code or False,
                'voucher_price': program.voucher_price or 0,
                'max_usage_per_program': program.max_usage_per_program or 0,
                'min_quantity': program.min_quantity or 1,
                'order_amount_min': program.order_amount_min or 0,
                'reward_quantity': program.reward_quantity or 0,
                'disc_amount': program.disc_amount or 0,
                'disc_percent': program.disc_percent or 0,
                'disc_fixed_price': program.disc_fixed_price or 0,
                'disc_max_amount': program.disc_max_amount or 0,
                'max_usage_per_order': program.max_usage_per_order or 0,
                'max_usage_per_customer': program.max_usage_per_customer or 0,
                'tax_from_date': program.tax_from_date.strftime('%Y-%m-%d') if program.tax_from_date else None,
                'tax_to_date': program.tax_to_date.strftime('%Y-%m-%d') if program.tax_to_date else None,
                'name': program.name or None,
                'code': program.code or None,
                'applicability': program.applicability or None,
                'discount_apply_on': program.discount_apply_on or None,
                'state': program.state or None,
                'promotion_type': program.promotion_type or None,
                'combo_code': program.combo_code or None,
                'combo_name': program.combo_name or None,
                'discount_based_on': program.discount_based_on or None,
                'product_domain': program.product_domain or None,
                'reward_type': program.reward_type or None,
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = [
            'campaign_id', 'active', 'max_usage', 'limit_usage_per_order', 'limit_usage_per_customer', 'registering_tax',
            'incl_reward_in_order', 'voucher_program_id', 'voucher_product_variant_id', 'skip_card_rank', 'limit_usage',
            'with_code', 'voucher_price', 'max_usage_per_program', 'min_quantity', 'order_amount_min', 'reward_quantity',
            'disc_amount', 'disc_percent', 'disc_fixed_price', 'disc_max_amount', 'max_usage_per_order', 'name',
            'max_usage_per_customer', 'tax_from_date', 'tax_to_date', 'code', 'applicability', 'discount_apply_on',
            'state', 'promotion_type', 'combo_code', 'combo_name', 'discount_based_on', 'product_domain', 'reward_type'
        ]
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        vals = {}
        for field in field_update:
            vals.update({
                field: values.get(field) or None
            })
        data = []
        for program in self:
            vals.update({
                'id': program.id,
                'updated_at': program.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.append(vals)
        return data
