# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.osv import expression

class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_pos_ui_res_partner_search(self, params):
        search_params = self._loader_params_res_partner()
        domain = expression.AND([search_params['search_params']['domain'], params['domain']])
        search_params['search_params']['domain'] = domain
        return self.env['res.partner'].search_read(**search_params['search_params'])

    @api.model
    def _pos_ui_models_to_load(self):
        res = super(PosSession, self)._pos_ui_models_to_load()
        if 'res.partner' in res:
            res.remove('res.partner')

        return res