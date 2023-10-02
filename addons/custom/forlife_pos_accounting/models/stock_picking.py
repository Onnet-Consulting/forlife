from odoo import models, _, fields
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _prepare_stock_move_vals(self, first_line, order_lines):
        res = super()._prepare_stock_move_vals(first_line, order_lines)
        if first_line and first_line._name == 'pos.order.line':
            res['pos_order_line_id'] = first_line.id
        return res
