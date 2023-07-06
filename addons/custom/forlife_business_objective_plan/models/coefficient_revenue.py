# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CoefficientRevenue(models.Model):
    _name = 'coefficient.revenue'
    _description = 'Coefficient Revenue'

    name = fields.Char('Name', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position', ondelete='restrict', required=True)
    fixed_coefficient = fields.Float('Fixed Coefficient', default=0)
    pc_by_employee_ids = fields.One2many('percentage.complete.by.employee', inverse_name='coefficient_revenue_id', string='Direct revenue')
    pc_by_store_ids = fields.One2many('percentage.complete.by.store', inverse_name='coefficient_revenue_id', string='Indirect revenue')
    brand_id = fields.Many2one("res.brand", string="Brand", required=True)

    _sql_constraints = [
        ('unique_job_position', 'UNIQUE(job_id, brand_id)', 'Job Position must be unique per brand !')
    ]
