# -*- coding:utf-8 -*-

from odoo import api, fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    # FIXME: after install database, we need update this module again to set 'code' column to not null in DB
    code = fields.Char(string='Code', required=True, copy=False)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Only one Code   occurrence by employee')
    ]
