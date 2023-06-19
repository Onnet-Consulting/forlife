# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super(StockMove, self)._prepare_move_line_vals(quantity, reserved_quant)
        if self.purchase_line_id:
            vals.update({
                'purchase_uom': self.purchase_line_id.purchase_uom.id,
                'occasion_code_id': self.purchase_line_id.occasion_code_id.id,
                'work_production': self.purchase_line_id.production_id.id,
                'account_analytic_id': self.purchase_line_id.account_analytic_id.id,
            })
        return vals