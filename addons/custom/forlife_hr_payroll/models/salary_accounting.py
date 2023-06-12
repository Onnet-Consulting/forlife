# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class SalaryAccounting(models.Model):
    _name = "salary.accounting"
    _description = "Salary Accounting"
    _order = 'entry_id asc, purpose_id asc, analytic_account_id asc,' \
             'asset_id asc, production_id asc, occasion_code_id asc, id asc'

    salary_record_id = fields.Many2one('salary.record', string='Reference', ondelete="cascade",
                                       required=True, copy=False)
    accounting_config_id = fields.Many2one('salary.accounting.config', required=True, ondelete='restrict')
    entry_id = fields.Many2one(related='accounting_config_id.entry_id', store=True)
    purpose_id = fields.Many2one(related='accounting_config_id.purpose_id', store=True)
    expense_item_id = fields.Many2one('expense.item', related='accounting_config_id.entry_id.expense_item_id',
                                      store=True)
    title = fields.Char(related='accounting_config_id.entry_id.title')
    accounting_type = fields.Selection([('debit', 'Debit'), ('credit', 'Credit')], required=True)

    analytic_account_id = fields.Many2one('account.analytic.account', compute="_compute_record_fields", store=True)
    asset_id = fields.Many2one('assets.assets', compute="_compute_record_fields", store=True)
    production_id = fields.Many2one('forlife.production', compute="_compute_record_fields", store=True)
    occasion_code_id = fields.Many2one('occasion.code', compute="_compute_record_fields", store=True)
    record = fields.Reference(selection=[('salary.record.main', 'salary.record.main'),
                                         ('salary.total.income', 'salary.total.income'),
                                         ('salary.supplementary', 'salary.supplementary'),
                                         ('salary.arrears', 'salary.arrears')])
    debit = fields.Float(string='Debit', compute='_compute_accounting_value', store=True)
    credit = fields.Float(string='Credit', compute='_compute_accounting_value', store=True)
    account_id = fields.Many2one('account.account', compute='_compute_accounting_value', store=True)
    partner_id = fields.Many2one('res.partner', compute='_compute_accounting_value', store=True)

    move_id = fields.Many2one('account.move', string='Odoo FI')
    reverse_move_id = fields.Many2one('account.move', string='Reverse Odoo FI')
    is_tc_entry = fields.Boolean(string='TC Entry', compute='_compute_is_tc_entry', store=True)

    @api.depends('analytic_account_id', 'asset_id', 'salary_record_id')
    def _compute_is_tc_entry(self):
        for rec in self:
            accounting_date = rec.salary_record_id.get_accounting_date()
            rec.is_tc_entry = bool(self.env['salary.tc.entry'].search([
                '&', '|', '&',
                ('entry_type', '=', 'analytic'),
                ('analytic_account_id', '=', rec.analytic_account_id.id),
                '&',
                ('entry_type', '=', 'asset'),
                ('asset_id', '=', rec.asset_id.id),
                '&',
                ('from_date', '<=', accounting_date),
                ('to_date', '>=', accounting_date)
            ], limit=1))

    @api.depends('record')
    def _compute_record_fields(self):
        for rec in self:
            rec.analytic_account_id = rec.record.analytic_account_id
            rec.asset_id = rec.record.asset_id
            rec.production_id = rec.record.production_id
            rec.occasion_code_id = rec.record.occasion_code_id

    @api.depends('accounting_type', 'accounting_config_id', 'record')
    def _compute_accounting_value(self):
        for rec in self:
            field_id = rec.accounting_config_id.entry_id.salary_field_id.name
            debit = credit = 0
            amount = rec.record[field_id]
            if rec.accounting_type == 'debit':
                debit = amount
                accounting_config = rec.accounting_config_id
                account_id = accounting_config.debit_account_id
                if accounting_config.debit_partner_by_employee and hasattr(rec.record, 'employee_id'):
                    partner_id = rec.record.employee_id.partner_id.id
                else:
                    partner_id = accounting_config.debit_partner_id.id
            else:
                credit = amount
                accounting_config = rec.accounting_config_id
                account_id = accounting_config.credit_account_id
                if accounting_config.credit_partner_by_employee and hasattr(rec.record, 'employee_id'):
                    partner_id = rec.record.employee_id.partner_id.id
                else:
                    partner_id = accounting_config.credit_partner_id.id

            rec.debit = debit
            rec.credit = credit
            rec.partner_id = partner_id
            rec.account_id = account_id
