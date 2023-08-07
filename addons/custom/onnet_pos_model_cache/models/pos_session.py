from odoo import models, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)
ADMIN_ID = 2


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_model_data_from_cache(self, model_name, loading_info):
        fields_str = str(loading_info['search_params']['fields'])
        domain_str = str([list(item) if isinstance(item, (list, tuple)) else item for item in
                          loading_info['search_params']['domain']])
        pos_cache = self.env['pos.model.cache']
        cache_for_user = pos_cache.search([
            ('compute_user_id', '=', ADMIN_ID),
            ('domain', '=', domain_str),
            ('model_fields', '=', fields_str),
            ('model', '=', model_name),
            ('compute_company_id', '=', self.env.user.company_id.id)
        ])

        if not cache_for_user:
            cache_for_user = pos_cache.create({
                'domain': domain_str,
                'model_fields': fields_str,
                'compute_user_id': ADMIN_ID,
                'model': model_name,
                'compute_company_id': self.env.user.company_id.id
            })
            cache_for_user.refresh_cache()
        return cache_for_user[-1].cache2json()

    def _get_pos_ui_promotion_pricelist_item(self, params):
        if self.env.context.get('ignore_cache', False):
            return super()._get_pos_ui_promotion_pricelist_item(params)
        records = self._get_model_data_from_cache('promotion.pricelist.item', params)
        self._process_pos_ui_promotion_pricelist_item(records)
        return records

    def _get_pos_ui_product_product(self, params):
        if self.env.context.get('ignore_cache', False):
            return super()._get_pos_ui_product_product(params)
        records = self._get_model_data_from_cache('product.product', params)
        self._process_pos_ui_product_product(records)
        return records

    # TODO: cache the promotion program if needed
    # def _get_pos_ui_promotion_program(self, params):
    #     if self.env.context.get('ignore_cache', False):
    #         return super()._get_pos_ui_promotion_program(params)
    #     records = self._get_model_data_from_cache('promotion.program', params)
    #     self._process_pos_ui_promotion_program(records)
    #     return records

    def get_cached_products(self, start, end):
        records = self.get_products_from_cache()
        self._process_pos_ui_product_product(records)
        return records[start:end]

    def get_total_products_count(self):
        records = self.get_products_from_cache()
        return len(records)
