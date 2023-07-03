# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PercentageCompleteByStore(models.Model):
    _name = 'percentage.complete.by.store'
    _description = 'Percentage Complete By Store'
    _order = 'pc_by_employee_id, percentage desc, id desc'

    name = fields.Char('PC by store', required=True)
    pc_by_employee_id = fields.Many2one('percentage.complete.by.employee', 'PC by Employee', ondelete='cascade', copy=True)
    coefficient_revenue_id = fields.Many2one('coefficient.revenue', 'Coefficient revenue', ondelete='cascade', copy=True)
    percentage = fields.Float('Percentage', copy=True)
    ratio = fields.Float('Ratio', copy=True)

    def name_get(self):
        result = []
        for r in self:
            name = f"{r.name}: {r.ratio}"
            result.append((r.id, name))
        return result

    def clone_pc_by_store(self):
        self.copy(dict(name=f'{self.name} (Copy)'))
