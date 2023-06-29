from odoo import models, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_promotion_pricelist_item_from_cache(self):
        loading_info = self._loader_params_promotion_pricelist_item()
        fields_str = str(loading_info['search_params']['fields'])
        domain_str = str([list(item) if isinstance(item, (list, tuple)) else item for item in loading_info['search_params']['domain']])
        pos_cache = self.env['pos.model.cache']
        cache_for_user = pos_cache.search([
            ('compute_user_id', '=', SUPERUSER_ID),
            ('domain', '=', domain_str),
            ('model_fields', '=', fields_str),
            ('model', '=', 'promotion.pricelist.item')
        ])
        if not cache_for_user:
            cache_for_user = pos_cache.create({
                'domain': domain_str,
                'model_fields': fields_str,
                'compute_user_id': SUPERUSER_ID,
                'model': 'promotion.pricelist.item'
            })
            cache_for_user.refresh_cache()

        return cache_for_user[-1].cache2json()

    def _get_pos_ui_promotion_pricelist_item(self, params):
        if self.env.context.get('ignore_cache', False):
            return super()._get_pos_ui_promotion_pricelist_item(params)
        records = self.get_promotion_pricelist_item_from_cache()
        self._process_pos_ui_promotion_pricelist_item(records)
        return records

    def get_products_from_cache(self):
        loading_info = self._loader_params_product_product()
        fields_str = str(loading_info['search_params']['fields'])
        domain_str = str([list(item) if isinstance(item, (list, tuple)) else item for item in loading_info['search_params']['domain']])
        pos_cache = self.env['pos.model.cache']
        cache_for_user = pos_cache.search([
            ('compute_user_id', '=', SUPERUSER_ID),
            ('domain', '=', domain_str),
            ('model_fields', '=', fields_str),
            ('model', '=', 'product.product')
        ])

        if not cache_for_user:
            cache_for_user = pos_cache.create({
                'domain': domain_str,
                'model_fields': fields_str,
                'compute_user_id': SUPERUSER_ID,
                'model': 'product.product'
            })
            cache_for_user.refresh_cache()
        return cache_for_user[-1].cache2json()

    def _get_pos_ui_product_product(self, params):
        if self.env.context.get('ignore_cache', False):
            return super()._get_pos_ui_product_product(params)
        records = self.get_products_from_cache()
        self._process_pos_ui_product_product(records)
        return records[:100000]

    def get_cached_products(self, start, end):
        records = self.get_products_from_cache()
        self._process_pos_ui_product_product(records)
        return records[start:end]

    def get_total_products_count(self):
        records = self.get_products_from_cache()
        return len(records)
