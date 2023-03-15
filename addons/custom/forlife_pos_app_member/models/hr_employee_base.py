# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    # FIXME: after install database, we need update this module again to set 'code' column to not null in DB
    code = fields.Char(string='Code', required=True, copy=False)
    related_contact_ids = fields.Many2many(context={'active_test': False})
    partner_id = fields.Many2one('res.partner', readonly=True, context={'active_test': False}, ondelete="restrict")
    user_id = fields.Many2one(readonly=True)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Only one Code   occurrence by employee')
    ]

    @api.depends('partner_id')
    def _compute_related_contacts(self):
        super()._compute_related_contacts()
        for employee in self:
            employee.related_contact_ids |= employee.partner_id

    def action_related_contacts(self):
        res = super(HrEmployeeBase, self).action_related_contacts()
        res.update({
            'context': {'active_test': False}
        })
        return res

    def _inverse_work_contact_details(self):
        pass

    def _create_employee_partner(self):
        partner_group_id = self.env.ref('forlife_pos_app_member.partner_group_4').id
        for employee in self:
            employee.partner_id = self.env['res.partner'].sudo().create({
                "company_type": "person",
                "group_id": partner_group_id,
                "ref": employee.code,
                'name': employee.name,
                'image_1920': employee.image_1920,
                'company_id': employee.company_id.id,
                'active': False
            })
        return True

    @api.model_create_multi
    def create(self, vals_list):
        res = super(HrEmployeeBase, self).create(vals_list)
        res._create_employee_partner()
        return res
