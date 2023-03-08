# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class SalaryEntrySettings(models.Model):
    _name = 'salary.entry.settings'
    _description = 'Entry Setttings'

    salary_table_id = fields.Many2one('ir.model',
                                      domain="[('model', 'in', ['salary.record.main', 'salary.total.income', 'salary.supplementary', 'salary.arrears'])]",
                                      string='Table', required=True, ondelete="cascade")
    groupable_account_ids = fields.Many2many('account.account', string='Groupable Accounts')

    _sql_constraints = [
        ('unique_table', 'unique(salary_table_id)', 'The table must be unique !')
    ]
