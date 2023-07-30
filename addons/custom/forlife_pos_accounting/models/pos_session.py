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
        return new_data

    # def _create_bank_payment_moves(self, data):
    #     new_data = super(PosSession, self)._create_bank_payment_moves(data)
    #     store_partner = self.config_id.store_id.contact_id
    #     if data['payment_method_to_receivable_lines'] and store_partner:
    #         for payment, receivable_lines in data['payment_method_to_receivable_lines'].items():
    #             receivable_lines.filtered(lambda line: not line.partner_id).partner_id = store_partner
    #     return new_data
