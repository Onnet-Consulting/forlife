from odoo import models, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_model_data_from_cached(self, model_name):
        model_table = model_name.replace('.', '_')
        func_params = getattr(self, f'_loader_params_{model_table}', None)
        loading_info = func_params()
        fields_str = str(loading_info['search_params']['fields'])
        domain_str = str([list(item) if isinstance(item, (list, tuple)) else item for item in
                          loading_info['search_params']['domain']])
        pos_cache = self.env['pos.model.cache']
        cache_for_user = pos_cache.search([
            ('compute_user_id', '=', SUPERUSER_ID),
            ('domain', '=', domain_str),
            ('model_fields', '=', fields_str),
            ('model', '=', model_name)
        ])
        if not cache_for_user:
            cache_for_user = pos_cache.create({
                'domain': domain_str,
                'model_fields': fields_str,
                'compute_user_id': SUPERUSER_ID,
                'model': model_name
            })
            cache_for_user.refresh_cache()

        return cache_for_user[-1].cache2json()

    def _get_pos_ui_promotion_pricelist_item(self, params):
        if self.env.context.get('ignore_cache', False):
            return super()._get_pos_ui_promotion_pricelist_item(params)
        records = self.get_model_data_from_cached('promotion.pricelist.item')
        self._process_pos_ui_promotion_pricelist_item(records)
        return records

    def _get_pos_ui_promotion_program(self, params):
        if self.env.context.get('ignore_cache', False):
            return super()._get_pos_ui_promotion_program(params)
        records = self.get_model_data_from_cached('promotion.program')
        return records

    def _get_pos_ui_product_product(self, params):
        if self.env.context.get('ignore_cache', False):
            return super()._get_pos_ui_product_product(params)
        records = self.get_model_data_from_cached('product.product')
        self._process_pos_ui_product_product(records)
        # return records[:100000]
        return records

    def get_cached_products(self, start, end):
        records = self.get_products_from_cache()
        self._process_pos_ui_product_product(records)
        return records[start:end]

    def get_total_products_count(self):
        records = self.get_products_from_cache()
        return len(records)
