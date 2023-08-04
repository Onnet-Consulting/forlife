from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        new_data = super(PosSession, self)._create_cash_statement_lines_and_cash_move_lines(data)
        store_partner = self.config_id.store_id.contact_id
        if data['combine_cash_statement_lines'] and store_partner:
            data['combine_cash_statement_lines'].filtered(lambda line: not line.partner_id).partner_id = store_partner
        if data['split_cash_statement_lines'] and store_partner:
            data['split_cash_statement_lines'].filtered(lambda line: not line.partner_id).partner_id = store_partner
        split_receivables_cash = data.get('split_receivables_cash')
        combine_receivables_cash = data.get('combine_receivables_cash')
        for payment, amounts in split_receivables_cash.items():
            journal_id = payment.payment_method_id.journal_id.id
            payment_ref = payment.name
            self.env['account.move'].search([
                ('pos_session_id', '=',  self.id),
                ('journal_id', '=', journal_id),
                ('payment_ref', '=', payment_ref),
            ]).filtered(lambda line: not line.partner_id).partner_id = store_partner
        for payment_method, amounts in combine_receivables_cash.items():
            journal_id = payment_method.journal_id.id
            payment_ref = self.name
            payment_line = self.env['account.bank.statement.line'].search([
                ('pos_session_id', '=',  self.id),
                ('journal_id', '=', journal_id),
                ('payment_ref', '=', payment_ref),
            ])
            payment_line.mapped('move_id.line_ids').filtered(lambda line: not line.partner_id).partner_id = store_partner
        return new_data

    # Thiết lập đối tượng cửa hàng vào chi tiết bút toán PTTT có partner_id = False
    # ======================== #
    # 1.Trường hợp kết hợp các giao dịch thanh toán ngân hàng
    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        """ """
        result = super()._create_combine_account_payment(payment_method, amounts, diff_amount)
        store_partner = self.config_id.store_id.contact_id
        payment_method_receivable_line = result.filtered(
            lambda l: l.payment_id.pos_payment_method_id.id == payment_method.id and not l.partner_id)
        if store_partner and payment_method_receivable_line:
            payment_method_receivable_line.payment_id.move_id.line_ids.partner_id = store_partner
        return result

    # 2. Trường hợp tách các giao dịch thanh toán ngân hàng
    #  Case này partner_id luôn được thiết lập đối tượng là khách hàng tại method _create_split_account_payment
