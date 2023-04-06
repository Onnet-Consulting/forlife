# -*- coding:utf-8 -*-

from odoo import api, fields, models
from datetime import timedelta


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    quantity_refunded = fields.Integer('Quantity refunded')
    expire_change_refund_date = fields.Date('Expire change refund_date', compute='_compute_expire_change_refund_date')
    quantity_canbe_refund = fields.Integer('Quantity can be refund', compute='_compute_quantity_canbe_refund')

    @api.depends('order_id.date_order', 'product_id.number_days_change_refund')
    def _compute_expire_change_refund_date(self):
        for r in self:
            r.expire_change_refund_date = r.order_id.date_order.date() + timedelta(days=r.product_id.number_days_change_refund)

    @api.depends('qty', 'refunded_qty')
    def _compute_quantity_canbe_refund(self):
        for r in self:
            r.quantity_canbe_refund = r.qty - r.refunded_qty

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        result['expire_change_refund_date'] = orderline.expire_change_refund_date
        result['quantity_canbe_refund'] = orderline.quantity_canbe_refund
        return result
