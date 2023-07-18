# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ExpenseItem(models.Model):
    _name = 'expense.item'
    _description = 'Expense Item'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    group_id = fields.Many2one('expense.category', string='Group', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code, company_id)', 'Code must be unique per company !')
    ]
