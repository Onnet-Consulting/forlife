# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    address_home_id = fields.Many2one(readonly=True)

    def prepare_address_home_value(self):
        self.ensure_one()
        return {
            "company_type": "person",
            "group_id": self.env.ref('forlife_pos_app_member.partner_group_4').id,
            "name": self.name,
            "ref": self.code,
            "phone": self.work_phone
        }

    def create_home_address(self):
        if self.address_home_id:
            raise ValidationError(_("Address home of employee %s already exist") % self.name)
        address_home = self.env['res.partner'].create(self.prepare_address_home_value())
        self.write({'address_home_id': address_home.id})
        return True
