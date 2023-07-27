# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'


    def write(self, vals):
        for item in self:
            if not item.picking_id.date_done:
                continue
            vals['date'] = item.picking_id.date_done
        return super().write(vals)
