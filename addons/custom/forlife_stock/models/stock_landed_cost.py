# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    date = fields.Date('Date', default=fields.Date.context_today, copy=False, required=True,
                       states={}, tracking=True)

    def write(self, vals):
        res = super().write(vals)
        if 'date' in vals and self.account_move_id:
            self.account_move_id.date = vals.get('date')
        return res
