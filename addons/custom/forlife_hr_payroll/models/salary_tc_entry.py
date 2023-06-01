# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class SalaryTcEntry(models.Model):
    _name = 'salary.tc.entry'
    _description = 'Salary TC Entry'

    entry_type = fields.Selection([('analytic', 'CC'), ('asset', 'AUC')], string='Type',
                                  default='analytic', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Center', check_company=True)
    assets_id = fields.Many2one('assets.assets', string='Project Code', check_company=True)
    from_date = fields.Date(string='From Date', required=True)
    to_date = fields.Date(string='To Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    _sql_constraints = [
        (
            'unique_value',
            'UNIQUE(entry_type, analytic_account_id, assets_id, from_date, to_date)',
            'Already exist an record with the same values!'
        )
    ]

    @api.onchange('entry_type')
    def _onchange_entry_type(self):
        if self.entry_type == 'analytic':
            self.analytic_account_id = False
        else:
            self.assets_id = False
