# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        self.ensure_one()
        res = super(AccountMoveReversal, self).reverse_moves()
        for invoice_line_id in self.move_ids.invoice_line_ids.filtered(lambda x: x.stock_move_id):
            qty_invoiced = invoice_line_id.stock_move_id.qty_invoiced - invoice_line_id.quantity
            if qty_invoiced <= 0:
                qty_invoiced = 0
            invoice_line_id.stock_move_id.write({
                'qty_invoiced': qty_invoiced,
                'qty_refunded': 0,
            })
        return res
