# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=False, default=fields.Datetime.now,
                                help="Date at which the transfer has been processed or cancelled.")

    def _action_done(self):
        old_date_done = self.date_done
        res = super(StockPicking, self)._action_done()
        if old_date_done:
            self.date_done = old_date_done
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'date_done' in vals:
            self.move_ids.write({'date': self.date_done})
            self.move_line_ids.write({'date': self.date_done})
        return res
