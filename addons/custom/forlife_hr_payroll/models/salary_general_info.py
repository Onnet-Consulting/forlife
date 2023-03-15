# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SalaryGeneralInfo(models.AbstractModel):
    _name = 'salary.general.info'
    _description = 'salary.general.info'

    salary_record_id = fields.Many2one('salary.record', string='Reference', ondelete="cascade", required=True, copy=False)
    company_id = fields.Many2one('res.company', related='salary_record_id.company_id', string='Company', store=True, readonly=True)
    purpose_id = fields.Many2one('salary.record.purpose', string='Salary calculation purpose', required=True, ondelete='restrict')
    department_id = fields.Many2one('hr.department', string='Department', required=True, ondelete="restrict")
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Center', required=True, ondelete="restrict")
    project_code = fields.Char(string='Project Code')
    manufacture_order_code = fields.Char(string='Manufacture Order Code')
    internal_order_code = fields.Char(string='Internal Order Code')

    _sql_constraints = [
        (
            'unique_info',
            'UNIQUE(salary_record_id,purpose_id,department_id,analytic_account_id,project_code,manufacture_order_code,internal_order_code)',
            'The combination of Reference, Salary calculation purpose, Department, Cost Center, '
            'Project Code, Manufacture Order Code and Internal Order Code must be unique !'
        )
    ]
