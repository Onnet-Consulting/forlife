# -*- coding: utf-8 -*-

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id._get_promotion_program_ids():
            result += [
                'promotion.program',
                'promotion.combo.line',
                'promotion.reward.line',
                'month.data',
                'dayofmonth.data',
                'dayofweek.data',
            ]
        return result

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

    def _loader_params_promotion_program(self):
        print(self.config_id._get_promotion_program_ids().ids)
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
                    'promotion_type',
                    'with_code',
                    'apply_multi_program',
                    'discount_based_on',
                    'valid_product_ids',
                    'min_quantity',
                    'order_amount_min',
                    'reward_type',
                    'reward_quantity',
                    'reward_for_referring',
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
                'domain': [('id', 'in', self.config_id._get_promotion_program_ids().ids)],
                'fields': ['program_id', 'valid_product_ids', 'quantity']
            }
        }

    def _loader_params_promotion_reward_line(self,):
        return {
            'search_params': {
                'domain': [('id', 'in', self.config_id._get_promotion_program_ids().ids)],
                'fields': ['program_id', 'quantity_min', 'quantity', 'disc_amount', 'disc_percent', 'disc_fixed_price', 'disc_max_amount']
            }
        }

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
