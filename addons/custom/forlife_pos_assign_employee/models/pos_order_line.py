# -*- coding:utf-8 -*-

from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        result['assigned_employee'] = orderline.employee_id.name
        return result
