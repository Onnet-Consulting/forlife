# -*- coding:utf-8 -*-

from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                  domain="[('id', 'in', order_id.config_id.store_id.employee_ids.ids)]")
