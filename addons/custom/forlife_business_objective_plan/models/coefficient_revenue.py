# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CoefficientRevenue(models.Model):
    _name = 'coefficient.revenue'
    _description = 'Coefficient Revenue'

    name = fields.Char('Name', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position', ondelete='restrict', required=True)
    fixed_coefficient = fields.Float('Fixed Coefficient', default=0)
    pc_by_employee_ids = fields.One2many('percentage.complete.by.employee', inverse_name='coefficient_revenue_id', string='Direct revenue')
    pc_by_store_ids = fields.One2many('percentage.complete.by.store', inverse_name='coefficient_revenue_id', string='Indirect revenue')
    brand_id = fields.Many2one("res.brand", string="Brand", required=True)

    @api.constrains("from_date", "to_date", "brand_id", "job_id")
    def validate_time(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))
            domain = ['&', '&', '&', ('brand_id', '=', self.brand_id.id), ('id', '!=', self.id), ('job_id', '=', self.job_id.id),
                      '|', '|', '&', ('from_date', '<=', self.from_date), ('to_date', '>=', self.from_date),
                      '&', ('from_date', '<=', self.to_date), ('to_date', '>=', self.to_date),
                      '&', ('from_date', '>', self.from_date), ('to_date', '<', self.to_date)]
            if self.search_count(domain) > 0:
                raise ValidationError(_("Time of coefficient revenue '[%s] %s' is overlapping.") % (record.id, record.name))
