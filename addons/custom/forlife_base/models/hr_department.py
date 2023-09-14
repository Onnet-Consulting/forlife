# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class HrDepartment(models.Model):
    _inherit = 'hr.department'
    _rec_names_search = ['code', 'name', 'complete_name']

    code = fields.Char(string='Code', copy=False)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code,company_id)', 'Department code must be unique!')
    ]

    def name_get(self):
        result = []
        for dp in self:
            if dp.code:
                name = f'[{dp.code}]{dp.complete_name}'
            else:
                name = f'{dp.complete_name}'
            result.append((dp.id, name))
        return result

