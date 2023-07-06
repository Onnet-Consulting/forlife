# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PercentageCompleteByEmployee(models.Model):
    _name = 'percentage.complete.by.employee'
    _description = 'Percentage Complete By Employee'
    _order = 'coefficient_revenue_id, percentage desc, id desc'

    name = fields.Char('PC by employee', required=True, copy=True)
    coefficient_revenue_id = fields.Many2one('coefficient.revenue', 'Coefficient revenue', ondelete='restrict', required=True, copy=True)
    percentage = fields.Float('Percentage', copy=True)
    pc_by_store_ids = fields.One2many('percentage.complete.by.store', inverse_name='pc_by_employee_id', string='Pc by store', copy=True)

    def clone_pc_by_employee(self):
        self.copy(dict(name=f'{self.name} (Copy)'))
