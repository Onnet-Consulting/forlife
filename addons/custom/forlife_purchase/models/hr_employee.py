# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class HrEmployeePrivate(models.Model):
    _inherit = 'hr.employee'

    code = fields.Char(string='Code')  # Mã nhân viên

