# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SalaryTotalIncome(models.Model):
    _name = 'salary.total.income'
    _inherit = 'salary.general.info'
    _description = 'Salary Total Income'  # Tổng thu nhập

    x_ttn = fields.Float(string='Total Income', required=True)
    note = fields.Text(string='Note')

    @api.constrains('x_ttn')
    def _check_x_ttn(self):
        for rec in self:
            if rec.x_ttn < 0:
                raise ValidationError(_("'Total income' in Salary total income table must >= 0!"))
