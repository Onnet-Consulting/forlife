# -*- coding:utf-8 -*-

from odoo import api, fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    code = fields.Char(string='Code', required=True)
