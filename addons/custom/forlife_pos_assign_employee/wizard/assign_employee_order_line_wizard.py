# -*- coding:utf-8 -*-

from odoo import api, fields, models


class AssignEmployeeOrderLineWizard(models.TransientModel):
    _name = 'assign.employee.order.line.wizard'
    _description = 'Assign Employee for Order Line Wizard'

    order_id = fields.Many2one('pos.order', string='Order')
    order_lines = fields.Many2many('pos.order.line', string='Order Lines', domain="[('order_id', '=', order_id)]")
    assignable_employees = fields.Many2many('hr.employee', string='Employees', readonly=True)
