# -*- coding: utf-8 -*-

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id._get_promotion_program_ids():
            result += [
                'surprising.reward.product.line',
                'promotion.program',
                'promotion.combo.line',
                'promotion.reward.line',
                'promotion.pricelist.item',
                'month.data',
                'dayofmonth.data',
                'dayofweek.data',
                'hour.data',
            ]
        return result

    def _loader_params_promotion_pricelist_item(self, ):
        product_id = self._get_product_ids_by_store()
        return {
            'search_params': {
                'domain': ['&', '&',
                           ('program_id', 'in', self.config_id._get_promotion_program_ids().ids),
                           ('active', '=', True),
                           '|', ('product_id.id', 'in', product_id), ('product_id.detailed_type', '=', 'service')],
                'fields': ['id', 'program_id', 'product_id', 'display_name', 'fixed_price', 'lst_price']
            }
        }

    def _get_pos_ui_promotion_pricelist_item(self, params):
        items = self.env['promotion.pricelist.item'].search_read(**params['search_params'], order='fixed_price DESC')
        res_items = self._process_pos_ui_promotion_pricelist_item(items)
        return res_items

    def _process_pos_ui_promotion_pricelist_item(self, items):
        res = []
        product_set = set()
        product_ids = set(self._get_product_ids_by_store())
        for item in items:
            product_id = item.get('product_id') and item.get('product_id')[0] or None
            if product_id not in product_set and item.get('lst_price') > item.get('fixed_price') \
                    and product_id in product_ids:
                res.append(item)
                product_set.add(product_id)
        items[:] = res

    def get_pos_ui_promotion_price_list_item_by_params(self, custom_search_params):
        """
        :param custom_search_params: a dictionary containing params of a search_read()
        """
        product_set = set()
        pricelist_items = self.env['promotion.pricelist.item'].browse()
        params = self._loader_params_promotion_pricelist_item()
        # custom_search_params will take priority
        params['search_params'] = dict(**params['search_params'], **custom_search_params)
        result = self.env['promotion.pricelist.item'].with_context(active_test=False).search(
            domain=params['search_params']['domain'],
            offset=params['search_params']['offset'],
            limit=params['search_params']['limit']).sorted(key='fixed_price', reverse=False)
        for item in result:
            if item.product_id.lst_price > item.fixed_price:
                pricelist_items |= item
                product_set.add(item.product_id.id)
        return pricelist_items.read(params['search_params']['fields'])

    def _get_pos_ui_promotion_pricelist_item(self, params):
        product_set = set()
        pricelist_items = self.env['promotion.pricelist.item'].browse()
        result = self.env['promotion.pricelist.item'].search(params['search_params']['domain']).sorted(key='fixed_price', reverse=False)
        for item in result:
            if item.product_id.id not in product_set and item.product_id.lst_price > item.fixed_price:
                pricelist_items |= item
                product_set.add(item.product_id.id)
        return pricelist_items.read(self._loader_params_promotion_pricelist_item()['search_params']['fields'])

    def _loader_params_month_data(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'code']
            }
        }

    def _loader_params_dayofmonth_data(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'code']
            }
        }

    def _loader_params_dayofweek_data(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'code']
            }
        }

    def _loader_params_hour_data(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'code']
            }
        }

    def _loader_params_surprising_reward_product_line(self):
        return {
            'search_params': {
                'domain': [('campaign_id', 'in', self.config_id._get_promotion_campaign_ids().ids), ('active', '=', True)],
                'fields': [
                    'id',
                    'to_check_product_ids',
                    'reward_code_program_id',
                    'has_check_product',
                    'max_quantity',
                    'issued_qty'
                ]
            }
        }

    def _loader_params_promotion_program(self):
        return {
            'search_params': {
                'domain': [('id', 'in', self.config_id._get_promotion_program_ids().ids)],
                'fields': [
                    'name',
                    'from_date',
                    'to_date',
                    'month_ids',
                    'dayofmonth_ids',
                    'dayofweek_ids',
                    'hour_ids',
                    'discount_apply_on',
                    'limit_usage',
                    'max_usage',
                    'limit_usage_per_order',
                    'max_usage_per_order',
                    'limit_usage_per_customer',
                    'max_usage_per_customer',
                    'limit_usage_per_program',
                    'max_usage_per_program',
                    'qty_per_combo',
                    'promotion_type',
                    'with_code',
                    'discount_based_on',
                    'json_valid_product_ids',
                    'min_quantity',
                    'order_amount_min',
                    'is_original_price',
                    'incl_reward_in_order',
                    'incl_reward_in_order_type',
                    'reward_type',
                    'voucher_program_id',
                    'voucher_product_variant_id',
                    'voucher_price',
                    'qty_min_required',
                    'reward_quantity',
                    'progressive_reward_compute',
                    'discount_product_ids',
                    'reward_product_ids',
                    'disc_amount',
                    'disc_percent',
                    'disc_fixed_price',
                    'disc_max_amount'],
            },
        }

    def _loader_params_promotion_combo_line(self,):
        return {
            'search_params': {
                'domain': [('program_id', 'in', self.config_id._get_promotion_program_ids().ids)],
                'fields': ['program_id', 'json_valid_product_ids', 'quantity']
            }
        }

    def _loader_params_promotion_reward_line(self,):
        return {
            'search_params': {
                'domain': [('program_id', 'in', self.config_id._get_promotion_program_ids().ids)],
                'fields': ['program_id', 'quantity_min', 'quantity', 'disc_amount', 'disc_percent', 'disc_fixed_price', 'disc_max_amount']
            }
        }

    def _get_pos_ui_surprising_reward_product_line(self, params):
        return self.env['surprising.reward.product.line'].search_read(**params['search_params'])

    def _get_pos_ui_promotion_program(self, params):
        return self.env['promotion.program'].search_read(**params['search_params'])

    def _get_pos_ui_promotion_combo_line(self, params):
        return self.env['promotion.combo.line'].search_read(**params['search_params'])

    def _get_pos_ui_promotion_reward_line(self, params):
        return self.env['promotion.reward.line'].search_read(**params['search_params'])

    def _get_pos_ui_month_data(self, params):
        return self.env['month.data'].search_read(**params['search_params'])

    def _get_pos_ui_dayofmonth_data(self, params):
        return self.env['dayofmonth.data'].search_read(**params['search_params'])

    def _get_pos_ui_dayofweek_data(self, params):
        return self.env['dayofweek.data'].search_read(**params['search_params'])

    def _get_pos_ui_hour_data(self, params):
        return self.env['hour.data'].search_read(**params['search_params'])
