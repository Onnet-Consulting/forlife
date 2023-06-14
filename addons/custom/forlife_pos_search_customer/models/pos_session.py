# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.osv import expression

class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_pos_ui_res_partner_search(self, params):
        # FIXME: Why this function is placed here ?, should be under res.partner
        search_params = self._loader_params_res_partner()
        domain = expression.AND([search_params['search_params']['domain'], params['domain']])
        search_params['search_params']['domain'] = domain
        partner = self.env['res.partner'].with_context(ignore_order_by=True)
        return partner.search_read(**search_params['search_params'], limit=80)

    def _load_model(self, model):
        if model == 'res.partner':
            return []
        return super(PosSession, self)._load_model(model)