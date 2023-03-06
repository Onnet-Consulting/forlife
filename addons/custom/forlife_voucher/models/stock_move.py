from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder)
        for move in res:
            # chỉ áp dụng với phiếu xuất bán - có đi kèm đơn bán hàng
            if move.state != 'done' or not move.product_id.voucher or not (move.sale_line_id or move.purchase_line_id):
                continue
            lot_name = move.mapped('move_line_ids').mapped('lot_id').mapped('name')
            if not lot_name:
                continue
            # trường hợp bán voucher
            if move.picking_type_id.code == 'outgoing':
                voucher_ids = self.env['voucher.voucher'].search([
                    ('name', 'in', lot_name), ('state', '=', 'new'),
                    ('product_voucher_id', '=', move.product_id.product_tmpl_id.id)
                ])
                voucher_ids.update({
                    'state': 'sold',
                    'sale_id': move.sale_line_id.order_id.id
                })
            # trường hợp mua voucher
            if move.picking_type_id.code == 'incoming':
                voucher_ids = self.env['voucher.voucher'].search([
                    ('name', 'in', lot_name), ('product_voucher_id', '=', move.product_id.product_tmpl_id.id)
                ])
                voucher_ids.update({
                    'purchase_id': move.purchase_line_id.order_id.id
                })
        return res
