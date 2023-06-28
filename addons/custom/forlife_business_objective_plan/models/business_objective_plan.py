# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BusinessObjectivePlan(models.Model):
    _name = 'business.objective.plan'
    _description = 'Business objective plan'

    name = fields.Char('Name', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    brand_id = fields.Many2one("res.brand", string="Brand", required=True)
    bo_store_ids = fields.One2many('business.objective.store', 'bo_plan_id', 'Business objective store')
    bo_employee_ids = fields.One2many('business.objective.employee', 'bo_plan_id', 'Business objective employee')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))
