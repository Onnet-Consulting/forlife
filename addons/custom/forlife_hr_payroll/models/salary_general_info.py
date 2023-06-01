# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SalaryGeneralInfo(models.AbstractModel):
    _name = 'salary.general.info'
    _description = 'Salary general info'

    salary_record_id = fields.Many2one('salary.record', string='Reference', ondelete="cascade", required=True,
                                       copy=False)
    company_id = fields.Many2one('res.company', related='salary_record_id.company_id', string='Company', store=True,
                                 readonly=True)
    purpose_id = fields.Many2one('salary.record.purpose', string='Salary calculation purpose', required=True,
                                 ondelete='restrict')
    department_id = fields.Many2one('hr.department', string='Department', required=True, ondelete="restrict")
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Center', required=True,
                                          ondelete="restrict")
    asset_id = fields.Many2one('assets.assets', string='Project Code')
    production_id = fields.Many2one('forlife.production', string='Manufacture Order Code')
    occasion_code_id = fields.Many2one('occasion.code', string='Internal Order Code')

    project_code = fields.Char(string='Project Code')
    manufacture_order_code = fields.Char(string='Manufacture Order Code')
    internal_order_code = fields.Char(string='Internal Order Code')

    _sql_constraints = [
        (
            'unique_value',
            'UNIQUE(salary_record_id, purpose_id, department_id, analytic_account_id, asset_id, production_id, occasion_code_id)',
            'The combination of Reference, Salary calculation purpose, Department, Cost Center, '
            'Project Code, Manufacture Order Code and Internal Order Code must be unique !'
        )
    ]
