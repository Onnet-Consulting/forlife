# -*- coding:utf-8 -*-

from odoo import models, fields, api, _

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        values = super(PosSession, self)._loader_params_product_product()

        values['search_params']['fields'].append('is_product_auto')
        values['search_params']['fields'].append('is_voucher_auto')
        return values

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        reason_refund_ids = self.env['pos.reason.refund'].search(
            [('brand_id', '=', self.config_id.store_id.brand_id.id)])
        reason = [{
            'id': rr.id,
            'name': rr.name,
            'brand_id': rr.brand_id.id
        } for rr in reason_refund_ids]
        loaded_data.update({
            'pos.reason.refund': reason
        })
        return loaded_data
