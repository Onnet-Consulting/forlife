# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
class SupplierInfo(models.Model):

    _inherit = 'product.supplierinfo'

    def _get_department_default(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.department_default_id

    def _get_team_default(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.team_default_id

    department_id = fields.Many2one('hr.department', string='Department', default=_get_department_default)
    team_id = fields.Many2one('hr.team', string='Team', default=_get_team_default)