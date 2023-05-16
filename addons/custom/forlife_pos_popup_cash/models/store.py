from odoo import api, fields, models


class Store(models.Model):
    _inherit = 'store'

    account_intermediary_pos = fields.Many2one('account.account', "Account intermediary")
    other_receivable_account_id = fields.Many2one(
        'account.account', company_dependent=True, string='Other Receivable Account',
        domain="[('deprecated', '=', False), ('company_id', '=', current_company_id)]")
    other_payable_account_id = fields.Many2one(
        'account.account', company_dependent=True, string='Other Payable Account',
        domain="[('deprecated', '=', False), ('company_id', '=', current_company_id)]")
    # TK tien van phong
    default_office_cash_account_id = fields.Many2one(
        'account.account', company_dependent=True, string='Default Office Account',
        domain="[('deprecated', '=', False), ('company_id', '=', current_company_id)]")

    receipt_expense_journal_id = fields.Many2one('account.journal', string='Receipt/Expense Journal')
