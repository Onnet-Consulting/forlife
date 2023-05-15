# -*- coding:utf-8 -*-

from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        result['assigned_employee'] = orderline.employee_id.name
        result['employee_id'] = orderline.employee_id.id
        return result

    @api.model
    def _log_message(self, order, value):
        order.message_post_with_view('forlife_pos_assign_employee.track_order_line_employee_changed', values={'value': value})

    def write(self, vals):
        log_values = []
        if 'employee_id' in vals:
            new_employee_name = self.env['hr.employee'].browse(vals.get('employee_id')).name
            for line in self:
                log_values.append({
                    'order': line.order_id,
                    'product': line.product_id.display_name,
                    'from_employee': line.employee_id.name or '',
                    'to_employee': new_employee_name
                })
        res = super(PosOrderLine, self).write(vals)
        for value in log_values:
            order = value.pop('order')
            self._log_message(order, value)
        return res
