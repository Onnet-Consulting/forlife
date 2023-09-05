# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def name_get(self):
        result = []
        for employee in self:
            if employee.code:
                name = f'{employee.code} - {employee.name}'
            else:
                name = f'{employee.name}'
            result.append((employee.id, name))
        return result

