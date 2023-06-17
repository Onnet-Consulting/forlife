# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super(StockMove, self)._prepare_move_line_vals(quantity, reserved_quant)
        if self.purchase_line_id and self.purchase_line_id.order_id.is_return:
            vals.update({
                'purchase_uom': self.purchase_line_id.purchase_uom.id,
            })
        return vals