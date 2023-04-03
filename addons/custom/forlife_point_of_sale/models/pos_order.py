# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        if not self.partner_id.store_fo_ids.filtered(lambda f: f.brand_id == self.config_id.store_id.brand_id):
            self.with_delay().create_store_first_order()
        return res

    def create_store_first_order(self):
        self.env['store.first.order'].sudo().create({
            'customer_id': self.partner_id.id,
            'brand_id': self.config_id.store_id.brand_id.id,
            'store_id': self.config_id.store_id.id,
        })
