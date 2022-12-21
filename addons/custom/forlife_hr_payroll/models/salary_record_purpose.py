# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SalaryRecordPurpose(models.Model):
    _name = 'salary.record.purpose'
    _description = 'Salary Record Purpose'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Only one code occurrence by salary record purpose')
    ]
