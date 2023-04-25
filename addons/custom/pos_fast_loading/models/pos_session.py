# -*- coding: utf-8 -*-
#
from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_pos_ui_mongo_server_config(self, params):
        return self.env['mongo.server.config'].search_read(**params['search_params'])

    def _loader_params_mongo_server_config(self):
        return {
            'search_params': {
                'domain': [('active_record', '=', True)],
                'fields': ['cache_last_update_time', 'pos_live_sync', 'active_record'],
            },
        }

    def load_pos_data(self):
        _logger.info('-------------- load_pos_data -----: %s', self._context)
        return super(PosSession, self).load_pos_data()

    @api.model
    def _pos_ui_models_to_load(self):
        res = super(PosSession, self)._pos_ui_models_to_load()
        if 'product.product' in res:
            res.remove('product.product')
        if 'mongo.server.config' not in res:
            res.append('mongo.server.config')
        return res