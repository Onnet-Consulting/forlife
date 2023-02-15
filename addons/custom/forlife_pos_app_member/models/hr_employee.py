# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_create_related_user(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Only the administrator can create User from Employee"))
        ResUser = self.env['res.users']
        default_company_id = self.env.company.id
        for employee in self.filtered(lambda x: not x.user_id):
            new_user = ResUser.create({
                'login': employee.code,
                'name': employee.name,
                'company_id': employee.company_id.id or default_company_id,
                'company_ids': [employee.company_id.id or default_company_id],
            })
            if employee.resource_id:
                employee.resource_id.write({'user_id': new_user.id})
            else:
                employee.write({'user_id': new_user.id})
        return True

    def toggle_active(self):
        res = super(HrEmployee, self).toggle_active()
        archived_employees = self.filtered(lambda e: not e.active)
        archived_employees.mapped('user_id').sudo().write({'active': False})
        return res
