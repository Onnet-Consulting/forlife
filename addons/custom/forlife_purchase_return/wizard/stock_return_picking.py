# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo.exceptions import UserError
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    for_po = fields.Boolean()

    @api.model
    def default_get(self, fields):
        res = super(StockReturnPicking, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'stock.picking':
            if len(self.env.context.get('active_ids', list())) > 1:
                raise UserError(_("You may only return one picking at a time."))
            picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
            if picking.exists():
                res.update({
                    'picking_id': picking.id,
                    'for_po': True if picking.purchase_id else False
                })
        return res

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        res = super(StockReturnPicking, self)._prepare_stock_return_picking_line_vals_from_move(stock_move)
        if self.picking_id.purchase_id:
            quantity_returned = 0
            for move in stock_move.move_dest_ids:
                if not move.origin_returned_move_id or move.origin_returned_move_id != stock_move:
                    continue
                if move.state in ('partially_available', 'assigned'):
                    quantity_returned += sum(move.move_line_ids.mapped('reserved_qty'))
                elif move.state in ('done'):
                    quantity_returned += move.product_qty

            res.update({
                'quantity_init': stock_move.product_qty,
                'quantity_returned': quantity_returned,
                'quantity_remain': stock_move.product_qty - quantity_returned,
                'quantity': 0
            })
            if res.get('quantity_remain') <= 0:
                res = {}
        return res


class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    quantity_init = fields.Float("Quantity Init", digits='Product Unit of Measure')
    quantity_returned = fields.Float("Quantity Returned", digits='Product Unit of Measure')
    quantity_remain = fields.Float("Quantity Remain", digits='Product Unit of Measure')

    @api.onchange('quantity')
    def _onchange_quantity(self):
        if self.wizard_id.picking_id.purchase_id:
            if self.quantity > self.quantity_remain:
                raise UserError("Số lượng trả lại vượt quá số lượng cho phép. Vui lòng thiết lập lại.")
