# -*- coding: utf-8 -*-
from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        res.update({
            'origin_move_id': move.id,
            'issue_invoice_type': 'adjust',
        })
        return res
    
    def reverse_moves(self):
        action = super(AccountMoveReversal, self).reverse_moves()
        if len(self.move_ids) == 1:
            move_id = self.move_ids[0]
            for refund in self.new_move_ids:
                if refund.move_type == move_id.move_type:
                    refund.update({
                        'origin_move_id': move_id.id,
                        'issue_invoice_type': 'replace',
                    })
                else:
                    refund.update({
                        'origin_move_id': move_id.id,
                        'issue_invoice_type': 'adjust',
                    })
        return action
