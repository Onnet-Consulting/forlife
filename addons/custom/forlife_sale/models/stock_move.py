from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _account_entry_move(self, qty, description, svl_id, cost):
        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        for r in res:
            r.update({'narration': self.picking_id.note})
        return res
