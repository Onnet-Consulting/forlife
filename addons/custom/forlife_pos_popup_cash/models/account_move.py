# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_transfer_cash_2office = fields.Boolean(string='POS Transfer Cash to POS', readonly=True)
    pos_orig_amount = fields.Float(string='POS Original Transfer Amount', readonly=True)
    pos_adjusted_amount = fields.Float(string='POS Adjusted Amount', readonly=False)
    pos_trans_session_id = fields.Many2one('pos.session', readonly=True)
    pos_trans_diff_move_id = fields.Many2one(
        'account.move', readonly=True, string='POS Transfer Difference Move')
    pos_orig_trans_move_id = fields.Many2one('account.move', readonly=True, string='POS Original Transfer Move')

    def _check_pos_transfer_amount(self):
        self.ensure_one()
        store_id = self.pos_trans_session_id.config_id.store_id
        debit_amount = abs(self.pos_adjusted_amount)
        delta_amount = self.pos_orig_amount - debit_amount
        sign_compare = float_compare(delta_amount, 0, precision_rounding=self.currency_id.rounding)

        if self.pos_trans_diff_move_id:
            diff_move_debit_sum = sum(self.pos_trans_diff_move_id.line_ids.filtered(lambda line: line.debit).mapped('debit'))
            if not float_is_zero(diff_move_debit_sum - delta_amount, precision_rounding=self.currency_id.rounding):
                raise UserError(_('You must cancel the transfer difference journal entry first!'))
            else:
                return

        if not sign_compare:
            return
        else:
            office_cash_account_id = store_id.default_office_cash_account_id.id
            # less than amount transferred from POS
            if sign_compare > 0:
                debit_account = store_id.other_receivable_account_id.id
                credit_account = office_cash_account_id
            # more than amount transferred from POS
            elif sign_compare < 0:
                debit_account = office_cash_account_id
                credit_account = store_id.other_payable_account_id.id
        desc = 'POS-Office Transfer Diff: %s' % self.pos_trans_session_id.name or ''
        move_val = {
            'ref': desc,
            'move_type': 'entry',
            'narration': desc,
            'partner_id': store_id.contact_id.id,
            'company_id': self.company_id.id,
            'pos_trans_session_id': self.pos_trans_session_id.id,
            'pos_orig_trans_move_id': self.id,
            'line_ids': [
                # debit line
                (0, 0, {
                    'name': desc,
                    'partner_id': store_id.contact_id.id,
                    'account_id': debit_account,
                    'debit': delta_amount > 0 and delta_amount or -delta_amount,
                    'credit': 0.0,
                }),
                # credit line
                (0, 0, {
                    'name': desc,
                    'partner_id': store_id.contact_id.id,
                    'account_id': credit_account,
                    'debit': 0.0,
                    'credit': delta_amount > 0 and delta_amount or -delta_amount,
                }),
            ]
        }
        move = self.create(move_val)
        self.pos_trans_diff_move_id = move.id
        return move

    def _post(self, soft=True):
        posted = super(AccountMove, self)._post(soft=soft)
        for move in posted:
            # Kiểm tra trên bút toán điều chỉnh chênh lệch,
            # nếu bút toán chuyển tiền gốc đã được điều chỉnh bởi một bút toán khác thì không cho post
            # nếu chưa được gán bút toán điều chỉnh thì gán lại
            if move.pos_orig_trans_move_id:
                diff_move_of_origin = move.pos_orig_trans_move_id.pos_trans_diff_move_id
                if diff_move_of_origin and move.id != diff_move_of_origin.id:
                    raise UserError(_('Bạn không thể Vào sổ một bút toán chênh lệch tiền đã hủy,'
                                      ' vì bút toán gốc đã được điều chỉnh bởi một bút toán khác'))
                elif not diff_move_of_origin:
                    move.pos_orig_trans_move_id.pos_trans_diff_move_id = move.id

            if move.pos_transfer_cash_2office and move.pos_orig_amount:
                diff_move = move._check_pos_transfer_amount()
                if diff_move:
                    body = """<div>Created journal entry
                           <a href="#" data-oe-model="%s"
                           data-oe-id="%s"> %s</a>
                           due to pos transfer amount difference </div>""" \
                            % (diff_move._name, diff_move.id, diff_move.display_name)
                    move.message_post(body=body)
        return posted

    def button_cancel(self):
        super(AccountMove, self).button_cancel()
        # Set pos_trans_diff_move_id = False if journal entry of transfer difference is canceled
        for move in self:
            if move.pos_orig_trans_move_id and move.id == move.pos_orig_trans_move_id.pos_trans_diff_move_id.id:
                move.pos_orig_trans_move_id.pos_trans_diff_move_id = False

    # def button_draft(self):
    #     for move in self:
    #         if move.pos_trans_diff_move_id and move.pos_trans_diff_move_id.state in ('draft', 'posted'):
    #             raise UserError(_('You must set to draft and delete the journal entry related to pos transfer difference first!'))
    #     return super().button_draft()
