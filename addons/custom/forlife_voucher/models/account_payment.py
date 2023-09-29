from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends('journal_id', 'payment_type', 'payment_method_line_id')
    def _compute_outstanding_account_id(self):
        super(AccountPayment, self)._compute_outstanding_account_id()
        for pay in self:
            if pay.pos_payment_method_id and pay.pos_payment_method_id.is_voucher:
                pay.outstanding_account_id = pay.journal_id.default_account_id