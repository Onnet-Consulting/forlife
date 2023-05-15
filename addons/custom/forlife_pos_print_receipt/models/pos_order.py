# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _order_fields(self, ui_order):
        data = super(PosOrder, self)._order_fields(ui_order)
        data['note'] = ui_order.get('note') or ''
        return data
