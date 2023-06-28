# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PrintStampsBarcode(models.Model):
    _inherit = 'print.stamps.barcode'

    def _get_default_store(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.store_default_id

    store_id = fields.Many2one('store', string='Store', default=_get_default_store)