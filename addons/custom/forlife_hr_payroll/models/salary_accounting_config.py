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
                                       domain=[('deprecated', '=', False)])
    credit_account_id = fields.Many2one('account.account', string='Credit account', required=True,
                                        domain=[('deprecated', '=', False)])
    debit_partner_id = fields.Many2one('res.partner', string='Debit partner')
    credit_partner_id = fields.Many2one('res.partner', string='Credit partner')

    _sql_constraints = [
        ('unique_combination', 'UNIQUE(company_id, entry_id, purpose_id)',
         'The combination of Company, Entry and Purpose must be unique !')
    ]

    @api.constrains('entry_id', 'debit_account_id', 'debit_partner_id')
    def _check_debit_value(self):
        exist_config = self.search([('company_id', '=', self.env.company.id)])
        for rec in self:
            if exist_config.filtered(
                    lambda x: x != rec and x.entry_id == rec.entry_id and x.debit_account_id == rec.debit_account_id and x.debit_partner_id != rec.debit_partner_id):
                raise ValidationError(_('Invalid Debit partner !'))

    @api.constrains('entry_id', 'credit_account_id', 'credit_partner_id')
    def _check_credit_value(self):
        exist_config = self.search([('company_id', '=', self.env.company.id)])
        for rec in self:
            if exist_config.filtered(
                    lambda x: x != rec and x.entry_id == rec.entry_id and x.credit_account_id == rec.credit_account_id and x.credit_partner_id != rec.credit_partner_id):
                raise ValidationError(_('Invalid Credit partner !'))
