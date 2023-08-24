# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class DepartmentInCharge(models.Model):
    _name = 'department.in.charge'
    _description = 'DepartmentInCharge'

    department_id = fields.Many2one('hr.department', string='Department', ondelete="restrict")
    department_code = fields.Char(string='Department Code', related='department_id.code')
    user_ids = fields.Many2many('res.users', string='User in charge')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(department_id)', 'Department already exists !')
    ]


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_department_in_charge(self):
        departments = self.env['department.in.charge'].search(['|', ('user_ids', 'in', self.ids), ('user_ids', '=', False)]).mapped('department_id')
        return self.env['hr.department'].search([('id', 'child_of', departments.ids)]).ids
