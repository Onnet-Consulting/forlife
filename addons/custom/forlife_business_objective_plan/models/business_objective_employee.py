# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BusinessObjectiveEmployee(models.Model):
    _name = 'business.objective.employee'
    _description = 'Business objective employee'

    bo_plan_id = fields.Many2one('business.objective.plan', 'Business objective plan', ondelete='restrict', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_id = fields.Many2one('store', 'Store', ondelete='restrict', required=True)
    sale_province_id = fields.Many2one('res.sale.province', 'Sale Province', ondelete='restrict', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', ondelete='restrict', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position', ondelete='restrict')
    revenue_target = fields.Monetary('Revenue target')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)

    def btn_employee_transfer(self):
        self.ensure_one()
