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

    def _check_pos_transfer_amount(self, **kwargs):
        self.ensure_one()
        credit_account = kwargs.get('credit_account') or 0
        debit_account = kwargs.get('debit_account') or 0
        delta_amount = kwargs.get('delta_amount') or 0
        store_id = self.pos_trans_session_id.config_id.store_id
        if not any([credit_account, debit_account, delta_amount]):
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
            'journal_id': self.journal_id.id,
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
        body = """<div>Created journal entry
                   <a href="#" data-oe-model="%s"
                   data-oe-id="%s"> %s</a>
                   due to pos transfer amount difference </div>""" \
               % (move._name, move.id, move.display_name)
        self.message_post(body=body)
        return move

    def _post(self, soft=True):
        condition = (self._context.get('move_post_type') or '') == 'bt_thu_tien' and len(self.ids) == 1
        credit_account = False
        debit_account = False
        if condition:
            # Nếu context có move_post_type = bt_thu_tien thì thực hiện logic mới:
            # điều chỉnh nợ/có của bút toán hiện tại = Tiền chuyển điều chỉnh lại
            new_value = self.pos_adjusted_amount
            credit_line = self.line_ids.filtered(lambda f: f.credit > 0)
            debit_line = self.line_ids - credit_line
            credit_line = credit_line and credit_line[0]
            debit_line = debit_line and debit_line[0]
            credit_account = credit_line.account_id.id
            debit_account = debit_line.account_id.id
            if credit_line.credit != new_value:
                self.write({'line_ids': [
                    (1, debit_line.id, {'debit': new_value}),
                    (1, credit_line.id, {'credit': new_value})
                ]})
        posted = super(AccountMove, self)._post(soft=soft)
        if condition:
            # Sinh thêm bút toán thu tiền với trạng thái Dự thảo, tài khoản giống bút toán hiện tại,
            # giá trị Nợ/Có = Tiền chuyển ban đầu từ POS - Tiền chuyển điều chỉnh lại
            delta_amount = self.pos_orig_amount - self.pos_adjusted_amount
            self._check_pos_transfer_amount(credit_account=credit_account, debit_account=debit_account, delta_amount=delta_amount)
        else:
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
                    move._check_pos_transfer_amount()
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

    def action_post(self):
        """
        Kiểm tra hành động bấm Vào sổ của 1 bút toán thỏa mãn các điều kiện sau
            nếu là 1 bút toán đơn lẻ
            move_type = entry
            là Chuyển tiền đến VP
            Tiền chuyển ban đầu từ POS > Tiền chuyển điều chỉnh lại
            Tiền chuyển ban đầu từ POS != 0
            Tiền chuyển điều chỉnh lại != 0
        Thì mở popup để chọn loại bút toán
        """
        if (len(self.ids) == 1 and self._context.get('validate_analytic') and not self._context.get('move_post_type') and self.move_type == 'entry'
                and self.pos_transfer_cash_2office and self.pos_orig_amount and self.pos_adjusted_amount and self.pos_orig_amount > self.pos_adjusted_amount):
            return self.env['ir.actions.actions']._for_xml_id('forlife_pos_popup_cash.choose_type_of_move_wizard_action')
        return super().action_post()
