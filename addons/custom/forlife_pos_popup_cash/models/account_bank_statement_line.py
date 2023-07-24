from odoo import api, fields, models


class AccountBank(models.Model):
    _inherit = 'account.bank.statement.line'

    from_store_tranfer = fields.Many2one('pos.config', 'From POS?', readonly=True)
    to_store_tranfer = fields.Many2one('pos.config', 'To POS?', readonly=True)
    is_reference = fields.Boolean('Is Reference Tranfer?')
    pos_transfer_type = fields.Selection([
        ('1', 'Office'),
        ('2', 'Store'),
        ('3', 'Other Difference'),
        ('4', 'Buy Expense'),
    ], string='POS Transfer Type', default=False, readonly=True)
    pos_config_id = fields.Many2one(related='pos_session_id.config_id')
    expense_label_id = fields.Many2one('pos.expense.label', ondelete='restrict')
    reason = fields.Char('Reason')

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        if self.pos_transfer_type == '3' and self.pos_session_id:
            store = self.pos_session_id.config_id.store_id
            credit_account_id = store.other_payable_account_id.id or False
            debit_account_id = store.other_receivable_account_id.id or False
            if self.amount < 0.0 and debit_account_id:
                counterpart_account_id = debit_account_id
            elif self.amount > 0.0 and credit_account_id:
                counterpart_account_id = credit_account_id
        if self.pos_transfer_type == '4' and self.pos_session_id and self.amount < 0.0 and self.pos_session_id.config_id.store_id.contact_id.property_account_payable_id:
            counterpart_account_id = self.pos_session_id.config_id.store_id.contact_id.property_account_payable_id.id

        res = super(AccountBank, self)._prepare_move_line_default_vals(counterpart_account_id)
        if counterpart_account_id is None and self.to_store_tranfer or self.from_store_tranfer or self.is_reference:
            res[1]['account_id'] = self.pos_session_id.config_id.store_id.account_intermediary_pos.id
            res[1]['partner_id'] = self.pos_session_id.config_id.store_id.contact_id.id

        if self.pos_transfer_type in ['3', '4'] and self.pos_session_id:
            res[1]['partner_id'] = self.pos_session_id.config_id.store_id.contact_id.id
        return res
