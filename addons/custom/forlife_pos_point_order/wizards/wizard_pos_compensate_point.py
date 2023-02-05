# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_is_zero


class POSCompensatePoint(models.TransientModel):
    _name = 'pos.compensate.point'
    _description = "Compensate Point Wizard"

    order_ids = fields.Many2many(
        'pos.order', default=lambda self: self.env.context.get('active_ids'))
    reason = fields.Text(default='')

    def apply(self):
        self.order_ids.btn_compensate_points_all(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}
