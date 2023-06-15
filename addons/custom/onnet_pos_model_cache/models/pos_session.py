from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_promotion_pricelist_item_from_cache(self):
        loading_info = self._loader_params_promotion_pricelist_item()
        fields_str = str(loading_info['search_params']['fields'])
        domain_str = str([list(item) if isinstance(item, (list, tuple)) else item for item in loading_info['search_params']['domain']])
        pos_cache = self.env['pos.model.cache']
        cache_for_user = pos_cache.search([
            ('id', 'in', self.config_id.model_cache_ids.ids),
            ('compute_user_id', '=', self.env.uid),
            ('domain', '=', domain_str),
            ('model_fields', '=', fields_str),
            ('model', '=', 'promotion.pricelist.item')
        ])

        if not cache_for_user:
            cache_for_user = pos_cache.create({
                'config_id': self.config_id.id,
                'domain': domain_str,
                'model_fields': fields_str,
                'compute_user_id': self.env.uid,
                'model': 'promotion.pricelist.item'
            })
            cache_for_user.refresh_cache()

        return cache_for_user.cache2json()

    def _get_pos_ui_promotion_pricelist_item(self, params):
        """
        If limited_products_loading is active, prefer the native way of loading products.
        Otherwise, replace the way products are loaded.
            First, we only load the first 100000 products.
            Then, the UI will make further requests of the remaining products.
        """
        if self.env.context.get('ignore_cache', False):
            return super()._get_pos_ui_promotion_pricelist_item(params)
        records = self.get_promotion_pricelist_item_from_cache()
        self._process_pos_ui_promotion_pricelist_item(records)
        return records
