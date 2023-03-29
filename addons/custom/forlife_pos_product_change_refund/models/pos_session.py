# -*- coding:utf-8 -*-

from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        reason_refund_ids = self.env['pos.reason.refund'].search([])
        reason = [{
            'id': rr.id,
            'name': rr.name,
            'brand_id': rr.brand_id.id
        } for rr in reason_refund_ids]
        loaded_data.update({
            'pos.reason.refund': reason
        })
        return loaded_data
