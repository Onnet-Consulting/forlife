# -*- coding:utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'mssql.server']

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for move in self.filtered(lambda m: m.state == 'done'):
            pass
        return res

    def insert_purchase_picking_data(self):
        bravo_table = 'B30AccDocPurchase'
        moves = self.filtered(lambda m: m.purchase_line_id)

