# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeTransfer(models.Model):
    _name = 'employee.transfer'
    _description = 'Employee transfer'

    bo_plan_id = fields.Many2one('business.objective.plan', 'Business objective plan', ondelete='restrict')
    store_source_id = fields.Many2one('store', 'Store Source', ondelete='restrict', required=True)
    store_dest_id = fields.Many2one('store', 'Store Dest', ondelete='restrict', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', ondelete='restrict', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position', ondelete='restrict')
    revenue_target = fields.Monetary('Revenue target')
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    bo_employee_id = fields.Integer('BO employee', default=0)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def btn_confirm_employee_transfer(self):
        self.ensure_one()
