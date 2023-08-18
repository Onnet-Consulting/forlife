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

        if self.pos_transfer_type in ['1', '2'] and self.pos_session_id:
            label_0000 = self.env['pos.expense.label'].search([('code', '=', '0000')], limit=1)
            res[0]['expense_label_id'] = res[1]['expense_label_id'] = label_0000 and label_0000.id or False

        if self.pos_transfer_type in ['3'] and self.pos_session_id:
            if self.amount >= 0:
                label_4909 = self.env['pos.expense.label'].search([('code', '=', '4909')], limit=1)
                res[0]['expense_label_id'] = res[1]['expense_label_id'] = label_4909 and label_4909.id or False

            else:
                label_1909 = self.env['pos.expense.label'].search([('code', '=', '1909')], limit=1)
                res[0]['expense_label_id'] = res[1]['expense_label_id'] = label_1909 and label_1909.id or False

        if self.pos_transfer_type in ['4'] and self.pos_session_id and self.expense_label_id:
            res[0]['expense_label_id'] = res[1]['expense_label_id'] = self.expense_label_id.id

        if not self.pos_transfer_type and self.pos_session_id and self.journal_id.type == 'cash':
            format_brand_id = self.env.ref('forlife_point_of_sale.brand_format', False)
            tokyolife_brand_id = self.env.ref('forlife_point_of_sale.brand_tokyolife', False)
            if self.pos_config_id.store_id.brand_id.id == format_brand_id.id:
                label_4101 = self.env['pos.expense.label'].search([('code', '=', '4101')], limit=1)
                res[0]['expense_label_id'] = res[1]['expense_label_id'] = label_4101 and label_4101.id or False
            elif self.pos_config_id.store_id.brand_id.id == tokyolife_brand_id.id:
                label_4100 = self.env['pos.expense.label'].search([('code', '=', '4100')], limit=1)
                res[0]['expense_label_id'] = res[1]['expense_label_id'] = label_4100 and label_4100.id or False
        return res
