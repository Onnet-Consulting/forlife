# -*- coding: utf-8 -*-

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append('res.partner.group')
        return result

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        result['search_params']['fields'].extend(['birthday', 'gender'])
        return result

    def _get_pos_ui_res_partner_group(self, params):
        return self.env['res.partner.group'].search_read(**params['search_params'])

    def _loader_params_res_partner_group(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.env.ref('forlife_pos_1.partner_group_c').id)],
                'fields': ['name', 'id']}
        }
