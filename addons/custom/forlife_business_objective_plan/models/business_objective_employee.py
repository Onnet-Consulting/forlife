# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BusinessObjectiveEmployee(models.Model):
    _name = 'business.objective.employee'
    _description = 'Business objective employee'

    bo_plan_id = fields.Many2one('business.objective.plan', 'Business objective plan', ondelete='restrict', required=True)
    bo_plan_temp_id = fields.Many2one('business.objective.plan', 'BOP temp')
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_id = fields.Many2one('store', 'Store', ondelete='restrict', required=True)
    sale_province_id = fields.Many2one('res.sale.province', 'Sale Province', ondelete='restrict')
    employee_id = fields.Many2one('hr.employee', 'Employee', ondelete='restrict', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position', ondelete='restrict')
    revenue_target = fields.Monetary('Revenue target')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def btn_employee_transfer(self):
        self.ensure_one()
        context = dict(self._context, )
        action = self.env.ref('forlife_business_objective_plan.employee_transfer_action_confirm').read()[0]
        action['context'] = context
        return action

    @api.onchange('store_id')
    def onchange_store(self):
        self.sale_province_id = self.store_id.warehouse_id.sale_province_id

    @api.onchange('employee_id')
    def onchange_employee(self):
        self.job_id = self.employee_id.job_id
