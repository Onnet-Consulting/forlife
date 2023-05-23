# -*- coding:utf-8 -*-

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_store_default(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.store_default_id

    store_id = fields.Many2one('store', string='Store', default=_get_store_default)