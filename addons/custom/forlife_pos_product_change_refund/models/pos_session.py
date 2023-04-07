# -*- coding:utf-8 -*-

from odoo import models, fields, api, _

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        values = super(PosSession, self)._loader_params_product_product()

        values['search_params']['fields'].append('is_product_auto')
        return values