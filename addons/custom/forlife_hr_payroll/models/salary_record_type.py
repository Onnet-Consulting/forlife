# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SalaryRecordType(models.Model):
    _name = 'salary.record.type'
    _description = 'Salary Record Type'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    user_ids = fields.Many2many('res.users', string='Users')
    group_ids = fields.Many2many('res.groups', string='Groups')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Only one code occurrence by salary record type')
    ]
