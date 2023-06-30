# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BusinessObjectiveEmployee(models.Model):
    _name = 'business.objective.employee'
    _description = 'Business objective employee'

    bo_plan_id = fields.Many2one('business.objective.plan', 'Business objective plan', ondelete='restrict', required=True)
    brand_id = fields.Many2one("res.brand", string="Brand", related='bo_plan_id.brand_id', store=True)
    bo_plan_temp_id = fields.Many2one('business.objective.plan', 'BOP temp')
    from_date = fields.Date(string='From date', related='bo_plan_id.from_date', store=True)
    to_date = fields.Date(string='To date', related='bo_plan_id.to_date', store=True)
    store_id = fields.Many2one('store', 'Store', ondelete='restrict', required=True, domain="[('brand_id', '=', brand_id)]")
    sale_province_id = fields.Many2one('res.sale.province', 'Sale Province', ondelete='restrict')
    employee_id = fields.Many2one('hr.employee', 'Employee', ondelete='restrict', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position', ondelete='restrict')
    revenue_target = fields.Monetary('Revenue target', default=10000000)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)

    def btn_employee_transfer(self):
        self.ensure_one()
        context = dict(self._context,
                       default_employee_id=self.employee_id.id,
                       default_bo_plan_id=self.bo_plan_id.id,
                       default_store_source_id=self.store_id.id,
                       default_bo_employee_id=self.id,
                       default_job_id=self.job_id.id)
        action = self.env.ref('forlife_business_objective_plan.create_employee_transfer_action').read()[0]
        action['context'] = context
        return action

    @api.onchange('store_id')
    def onchange_store(self):
        self.sale_province_id = self.store_id.warehouse_id.sale_province_id

    @api.onchange('employee_id')
    def onchange_employee(self):
        self.job_id = self.employee_id.job_id
