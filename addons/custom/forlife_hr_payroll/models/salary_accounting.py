# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class SalaryAccounting(models.Model):
    _name = "salary.accounting"
    _description = "Salary Accounting"
    _order = 'entry_id asc, purpose_id asc, analytic_account_id asc, manufacture_order_code asc, project_code asc, internal_order_code asc, id asc'

    salary_record_id = fields.Many2one('salary.record', string='Reference', ondelete="cascade", required=True, copy=False)
    accounting_config_id = fields.Many2one('salary.accounting.config', required=True, ondelete='restrict')
    entry_id = fields.Many2one(related='accounting_config_id.entry_id', store=True)
    purpose_id = fields.Many2one(related='accounting_config_id.purpose_id', store=True)

    title = fields.Char(related='accounting_config_id.entry_id.title')
    accounting_type = fields.Selection([('debit', 'Debit'), ('credit', 'Credit')], required=True)

    analytic_account_id = fields.Many2one('account.analytic.account', compute="_compute_record_fields", store=True)
    manufacture_order_code = fields.Char(compute="_compute_record_fields", store=True)
    project_code = fields.Char(compute="_compute_record_fields", store=True)
    internal_order_code = fields.Char(compute="_compute_record_fields", store=True)

    record = fields.Reference(selection=[('salary.record.main', 'salary.record.main'),
                                         ('salary.total.income', 'salary.total.income'),
                                         ('salary.supplementary', 'salary.supplementary'),
                                         ('salary.arrears', 'salary.arrears')])
    debit = fields.Float(string='Debit', compute='_compute_accounting_value', store=True)
    credit = fields.Float(string='Credit', compute='_compute_accounting_value', store=True)
    account_id = fields.Many2one('account.account', compute='_compute_accounting_value', store=True)
    partner_id = fields.Many2one('res.partner', compute='_compute_accounting_value', store=True)

    move_id = fields.Many2one('account.move', string='Odoo FI')
    sap_move_ref = fields.Char(string='SAP FI')
    reverse_move_id = fields.Many2one('account.move', string='Reverse Odoo FI')
    reverse_sap_move_ref = fields.Char(string='Reverse SAP FI')

    @api.depends('record')
    def _compute_record_fields(self):
        for rec in self:
            rec.analytic_account_id = rec.record.analytic_account_id
            rec.manufacture_order_code = rec.record.manufacture_order_code
            rec.project_code = rec.record.project_code
            rec.internal_order_code = rec.record.internal_order_code

    @api.depends('accounting_type', 'accounting_config_id', 'record')
    def _compute_accounting_value(self):
        for rec in self:
            field_id = rec.accounting_config_id.entry_id.salary_field_id.name
            debit = credit = 0
            amount = rec.record[field_id]
            if rec.accounting_type == 'debit':
                debit = amount
                partner_id = rec.accounting_config_id.debit_partner_id
                account_id = rec.accounting_config_id.debit_account_id
            else:
                credit = amount
                partner_id = rec.accounting_config_id.credit_partner_id
                account_id = rec.accounting_config_id.credit_account_id

            rec.debit = debit
            rec.credit = credit
            rec.partner_id = partner_id
            rec.account_id = account_id
