# -*- coding:utf-8 -*-

from odoo import api, fields, models


class HrTeam(models.Model):
    _name = 'hr.team'
    _description = 'HR Team'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    department_id = fields.Many2one('hr.department', string='Department')