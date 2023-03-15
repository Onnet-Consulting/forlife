# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    def action_create_employee(self):
        # prevent create employee from user
        return
