# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SalaryRecordPurpose(models.Model):
    _name = 'salary.record.purpose'
    _description = 'Salary Record Purpose'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}"

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Only one code occurrence by salary record purpose')
    ]
