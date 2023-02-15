# -*- coding: utf-8 -*-
#
from odoo import api, fields, models, _


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_models_to_load(self):
        models_to_load = super(PosSession, self)._pos_ui_models_to_load()
        models_to_load.append('mongo.server.config')
        return models_to_load

    def _get_pos_ui_mongo_server_config(self, params):
        return self.env['mongo.server.config'].search_read(**params['search_params'])

    def _loader_params_mongo_server_config(self):
        return {
            'search_params': {
                'domain': [('active_record', '=', True)],
                'fields': ['cache_last_update_time', 'pos_live_sync', 'active_record'],
            },
        }

    # def _pos_data_process(self, loaded_data):
    #     super()._pos_data_process(loaded_data)
    #     loaded_data['mongo_config'] = loaded_data['mongo.server.config']
