# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    # FIXME: after install database, we need update this module again to set 'code' column to not null in DB
    code = fields.Char(string='Code', required=True, copy=False)
    related_contact_ids = fields.Many2many(context={'active_test': False})
    work_contact_id = fields.Many2one(context={'active_test': False})
    user_id = fields.Many2one(readonly=True)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Only one Code   occurrence by employee')
    ]

    def action_related_contacts(self):
        res = super(HrEmployeeBase, self).action_related_contacts()
        res.update({
            'context': {'active_test': False}
        })
        return res

    @api.depends('work_contact_id', 'work_contact_id.phone', 'work_contact_id.email')
    def _compute_work_contact_details(self):
        for employee in self:
            if employee.work_contact_id:
                employee.mobile_phone = employee.work_contact_id.phone
                employee.work_email = employee.work_contact_id.email

    def _inverse_work_contact_details(self):
        for employee in self:
            if not employee.work_contact_id:
                employee.work_contact_id = self.env['res.partner'].sudo().create({
                    "company_type": "person",
                    "group_id": self.env.ref('forlife_pos_app_member.partner_group_4').id,
                    "ref": self.code,
                    'phone': employee.mobile_phone,
                    'email': employee.work_email,
                    'name': employee.name,
                    'image_1920': employee.image_1920,
                    'company_id': employee.company_id.id,
                    'active': False
                })
            else:
                employee.work_contact_id.sudo().write({
                    'email': employee.work_email,
                    'phone': employee.mobile_phone,
                })
