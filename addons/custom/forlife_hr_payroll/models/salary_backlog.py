# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

NUMBER_FIELDS = ["amount"]


class SalaryBacklog(models.Model):
    _name = 'salary.backlog'
    _description = 'Salary Backlog'  # TỒN ĐỌNG

    salary_record_id = fields.Many2one('salary.record', string='Reference', ondelete="cascade", required=True, copy=False)
    company_id = fields.Many2one('res.company', related='salary_record_id.company_id', string='Company', store=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='restrict')
    department_id = fields.Many2one('hr.department', string='Department', required=True, ondelete="restrict")
    amount = fields.Float(string='Amount Money', required=True)
    month = fields.Integer(string='Month', required=True)
    year = fields.Integer(string='Year', required=True)
    period = fields.Char(compute='_compute_period', string='Period')

    @api.depends('month', 'year')
    def _compute_period(self):
        for record in self:
            record.period = f"{record.month:02d}.{record.year}"

    @api.constrains(*NUMBER_FIELDS)
    def _check_numbers(self):
        fields_desc = self.fields_get(NUMBER_FIELDS, ['string'])
        for rec in self:
            for num_field in NUMBER_FIELDS:
                if rec[num_field] < 0:
                    raise ValidationError(_("Field '%s' value in the table '%s' must be >= 0") % (fields_desc[num_field]['string'], self._description))
