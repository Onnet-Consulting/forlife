# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def reassign_employee(self):
        return {
            'name': _('Assign employee'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'assign.employee.order.line.wizard',
            'context': dict(
                self.env.context,
                default_order_id=self.id,
                default_order_lines=self.lines.ids,
                default_assignable_employees=self.session_id.config_id.store_id.employee_ids.ids
            ),
            'target': 'new'
        }
