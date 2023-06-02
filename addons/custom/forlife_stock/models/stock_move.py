# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    ref_asset = fields.Many2one('assets.assets', 'Thẻ tài sản')

    def _account_entry_move(self, qty, description, svl_id, cost):
        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        for item in res:
            if 'date' in item and self.picking_id.date_done:
                item['date'] = fields.Datetime.context_timestamp(self, self.picking_id.date_done).date()
        return res

    def write(self, vals):
        for item in self:
            if item.picking_id.date_done:
                vals['date'] = item.picking_id.date_done
                account_move_ids = self.env['account.move'].search([('stock_move_id', 'in', item.ids)])
                if account_move_ids:
                    account_move_ids.write({
                        'date': fields.Datetime.context_timestamp(self, item.picking_id.date_done).date()
                    })
        return super().write(vals)
