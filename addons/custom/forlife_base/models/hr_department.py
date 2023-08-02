# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    code = fields.Char(string='Code', copy=False)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code,company_id)', 'Department code must be unique!')
    ]
