# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CoefficientRevenue(models.Model):
    _name = 'coefficient.revenue'
    _description = 'Coefficient Revenue'

    name = fields.Char('Name', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position', ondelete='restrict', copy=False)
    fixed_coefficient_direct = fields.Float('Fixed Coefficient direct', default=0, copy=True)
    fixed_coefficient_indirect = fields.Float('Fixed Coefficient indirect', default=0, copy=True)
    pc_by_employee_ids = fields.One2many('percentage.complete.by.employee', inverse_name='coefficient_revenue_id', string='Direct revenue', copy=True)
    pc_by_store_ids = fields.One2many('percentage.complete.by.store', inverse_name='coefficient_revenue_id', string='Indirect revenue', copy=True)
    brand_id = fields.Many2one("res.brand", string="Brand", required=True, copy=True)

    _sql_constraints = [
        ('unique_job_position', 'UNIQUE(job_id, brand_id)', 'Job Position must be unique per brand !')
    ]
