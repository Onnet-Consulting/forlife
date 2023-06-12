# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class PromotionProgram(models.Model):
    _name = 'promotion.program'
    _inherit = ['promotion.program', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'campaign_id': line.campaign_id.id or None,
            'active': line.active or False,
            'max_usage': line.max_usage or 0,
            'limit_usage_per_order': line.limit_usage_per_order or False,
            'limit_usage_per_customer': line.limit_usage_per_customer or False,
            'registering_tax': line.registering_tax or False,
            'incl_reward_in_order': line.incl_reward_in_order or False,
            'voucher_program_id': line.voucher_program_id.id or False,
            'voucher_product_variant_id': line.voucher_product_variant_id.id or False,
            'skip_card_rank': line.skip_card_rank or False,
            'limit_usage': line.limit_usage or False,
            'with_code': line.with_code or False,
            'voucher_price': line.voucher_price or 0,
            'max_usage_per_program': line.max_usage_per_program or 0,
            'min_quantity': line.min_quantity or 1,
            'order_amount_min': line.order_amount_min or 0,
            'reward_quantity': line.reward_quantity or 0,
            'disc_amount': line.disc_amount or 0,
            'disc_percent': line.disc_percent or 0,
            'disc_fixed_price': line.disc_fixed_price or 0,
            'disc_max_amount': line.disc_max_amount or 0,
            'max_usage_per_order': line.max_usage_per_order or 0,
            'max_usage_per_customer': line.max_usage_per_customer or 0,
            'tax_from_date': line.tax_from_date.strftime('%Y-%m-%d') if line.tax_from_date else None,
            'tax_to_date': line.tax_to_date.strftime('%Y-%m-%d') if line.tax_to_date else None,
            'name': line.name or None,
            'code': line.code or None,
            'applicability': line.applicability or None,
            'discount_apply_on': line.discount_apply_on or None,
            'state': line.state or None,
            'promotion_type': line.promotion_type or None,
            'combo_code': line.combo_code or None,
            'combo_name': line.combo_name or None,
            'discount_based_on': line.discount_based_on or None,
            'product_domain': line.product_domain or None,
            'reward_type': line.reward_type or None,
            'apply_online': line.apply_online or False,
            'for_new_customer': line.for_new_customer or False,
            'product_ids': [{'id': p.id, 'sku': p.barcode} for p in line.product_ids],
            'combo_line_ids': [{'quantity': combo.quantity,
                                'product': [{'id': p.id, 'sku': p.barcode} for p in combo.product_ids]
                                } for combo in line.combo_line_ids],
        } for line in self]

    def get_field_update(self):
        return [
            'campaign_id', 'active', 'max_usage', 'limit_usage_per_order', 'limit_usage_per_customer', 'registering_tax',
            'incl_reward_in_order', 'voucher_program_id', 'voucher_product_variant_id', 'skip_card_rank', 'limit_usage',
            'with_code', 'voucher_price', 'max_usage_per_program', 'min_quantity', 'order_amount_min', 'reward_quantity',
            'disc_amount', 'disc_percent', 'disc_fixed_price', 'disc_max_amount', 'max_usage_per_order', 'name', 'apply_online',
            'max_usage_per_customer', 'tax_from_date', 'tax_to_date', 'code', 'applicability', 'discount_apply_on', 'for_new_customer',
            'state', 'promotion_type', 'combo_code', 'combo_name', 'discount_based_on', 'product_domain', 'reward_type', 'product_ids',
            'combo_line_ids',
        ]
