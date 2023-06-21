# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PointCompensateRequest(models.Model):
    _name = 'point.compensate.request'
    _description = 'Point Compensate Request'

    order_id = fields.Many2one('pos.order', required=True)
    compensated = fields.Boolean(string='Compensated', default=False)
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True)

    _sql_constraints = [
        ('unique_order', 'UNIQUE(order_id)', _('Order must be unique!'))
    ]
