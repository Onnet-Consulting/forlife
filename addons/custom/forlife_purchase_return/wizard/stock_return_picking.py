# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.addons.stock.wizard.stock_picking_return import ReturnPicking

import logging

_logger = logging.getLogger(__name__)


def _create_returns(self):
    # TODO sle: the unreserve of the next moves could be less brutal
    for return_move in self.product_return_moves.mapped('move_id'):
        return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()

    # create new picking for returned products
    new_picking = self.picking_id.copy(self._prepare_picking_default_values())
    picking_type_id = new_picking.picking_type_id.id
    new_picking.message_post_with_view('mail.message_origin_link',
                                       values={'self': new_picking, 'origin': self.picking_id},
                                       subtype_id=self.env.ref('mail.mt_note').id)
    returned_lines = 0
    for return_line in self.product_return_moves:
        # sửa lại base chỉ chọn những line được tích
        if not return_line.select_line:
            continue
        if not return_line.move_id:
            raise UserError(_("You have manually created product lines, please delete them to proceed."))
        # TODO sle: float_is_zero?
        if return_line.quantity:
            returned_lines += 1
            vals = self._prepare_move_default_values(return_line, new_picking)
            r = return_line.move_id.copy(vals)
            vals = {}

            # +--------------------------------------------------------------------------------------------------------+
            # |       picking_pick     <--Move Orig--    picking_pack     --Move Dest-->   picking_ship
            # |              | returned_move_ids              ↑                                  | returned_move_ids
            # |              ↓                                | return_line.move_id              ↓
            # |       return pick(Add as dest)          return toLink                    return ship(Add as orig)
            # +--------------------------------------------------------------------------------------------------------+
            move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
            # link to original move
            move_orig_to_link |= return_line.move_id
            # link to siblings of original move, if any
            move_orig_to_link |= return_line.move_id \
                .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel')) \
                .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel'))
            move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
            # link to children of originally returned moves, if any. Note that the use of
            # 'return_line.move_id.move_orig_ids.returned_move_ids.move_orig_ids.move_dest_ids'
            # instead of 'return_line.move_id.move_orig_ids.move_dest_ids' prevents linking a
            # return directly to the destination moves of its parents. However, the return of
            # the return will be linked to the destination moves.
            move_dest_to_link |= return_line.move_id.move_orig_ids.mapped('returned_move_ids') \
                .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel')) \
                .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel'))
            vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link]
            vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]
            r.write(vals)
    if not returned_lines:
        raise UserError(_("Please specify at least one non-zero quantity."))

    new_picking.action_confirm()
    new_picking.action_assign()
    return new_picking.id, picking_type_id


ReturnPicking._create_returns = _create_returns


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    for_po = fields.Boolean()
    return_reason = fields.Selection([
        ('invalid', 'Nhập sai'),
        ('faulty', 'Trả hàng do lỗi'),
        ('diff', 'Trả hàng do chênh lệch')
    ], string='Lí do trả hàng', required=True)

    select_all = fields.Boolean(string='Chọn tất cả', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['product_return_moves'] = [item for item in val.get('product_return_moves', []) if
                                           'quantity' in item[2] and item[2]['quantity'] >= 1]
        res = super().create(vals_list)
        return res

    @api.onchange('select_all')
    def _onchange_select_all(self):
        for rec in self.product_return_moves:
            if self.select_all:
                rec.update({'select_line': True})
            else:
                rec.update({'select_line': False})

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

    def _prepare_picking_default_values(self):
        res = super()._prepare_picking_default_values()
        res['return_reason'] = self.return_reason
        return res


class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    quantity_init = fields.Float("Quantity Init", digits='Product Unit of Measure')
    quantity_returned = fields.Float("Quantity Returned", digits='Product Unit of Measure')
    quantity_remain = fields.Float("Quantity Remain", digits='Product Unit of Measure')
    select_line = fields.Boolean(string=' ', default=False)

    @api.onchange('quantity')
    def _onchange_quantity(self):
        if self.wizard_id.picking_id.purchase_id:
            if self.quantity > self.quantity_remain:
                raise UserError("Số lượng trả lại vượt quá số lượng cho phép. Vui lòng thiết lập lại.")
