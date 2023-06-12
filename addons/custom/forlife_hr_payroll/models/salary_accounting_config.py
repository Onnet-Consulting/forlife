# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SalaryAccountingConfig(models.Model):
    _name = 'salary.accounting.config'
    _description = 'Salary Accounting Configuration'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    entry_id = fields.Many2one('salary.entry', string='Entry', required=True, ondelete="restrict")
    purpose_id = fields.Many2one('salary.record.purpose', string='Purpose', required=True, ondelete="restrict")
    debit_account_id = fields.Many2one('account.account', string='Debit account', required=True,
                                       domain=[('deprecated', '=', False)], check_company=True)
    credit_account_id = fields.Many2one('account.account', string='Credit account', required=True,
                                        domain=[('deprecated', '=', False)], check_company=True)
    debit_partner_id = fields.Many2one('res.partner', string='Debit partner')
    credit_partner_id = fields.Many2one('res.partner', string='Credit partner')
    debit_partner_by_employee = fields.Boolean(string='Debit partner by employee', default='False')
    credit_partner_by_employee = fields.Boolean(string='Credit partner by employee', default='False')

    _sql_constraints = [
        ('unique_combination', 'UNIQUE(company_id, entry_id, purpose_id, debit_account_id, credit_account_id)',
         'The combination of Company, Entry, Purpose, Debit account and Credit account must be unique !'),
        ('unique_combination_debit', 'UNIQUE(company_id, entry_id, debit_account_id, debit_partner_id, purpose_id)',
         'The combination of Company, Entry, Purpose, Debit account and Debit partner must be unique !'),
        ('unique_combination_credit', 'UNIQUE(company_id, entry_id, credit_account_id, credit_partner_id, purpose_id)',
         'The combination of Company, Entry, Purpose, Credit account and Credit partner must be unique !'),
    ]
