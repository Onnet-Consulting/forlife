# -*- coding:utf-8 -*-

from odoo import api, fields, models
from datetime import timedelta
import pytz


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    quantity_refunded = fields.Integer('Quantity refunded')
    expire_change_refund_date = fields.Date('Expire change refund_date', compute='_compute_expire_change_refund_date')
    quantity_canbe_refund = fields.Integer('Quantity can be refund', compute='_compute_quantity_canbe_refund')
    reason_refund_id = fields.Many2one('pos.reason.refund', 'Reason Refund')
    money_point_is_reduced = fields.Monetary('Money Point is reduced', compute='_compute_money_point_is_reduced_line')
    # price_unit_refund = fields.Float(string='Unit Price Refund', digits=0)
    # price_subtotal_incl_refund = fields.Float(string='Subtotal Refund', digits=0)
    is_product_defective = fields.Boolean('Là sản phẩm lỗi', default=False)
    money_reduce_from_product_defective = fields.Float()
    product_defective_id = fields.Many2one('product.defective')

    @api.depends('discount_details_lines.money_reduced')
    def _compute_money_point_is_reduced_line(self):
        for rec in self:
            rec.money_point_is_reduced = sum([dis.money_reduced for dis in rec.discount_details_lines.filtered(lambda x: x.type == 'point')])

    def _order_line_fields(self, line, session_id=None):
        res = super()._order_line_fields(line, session_id)
        if 'reason_refund_id' in res[2] and res[2].get('reason_refund_id', 0) < 1:
            res[2].pop('reason_refund_id')
        return res

    @api.depends('order_id.date_order', 'product_id.number_days_change_refund')
    def _compute_expire_change_refund_date(self):
        for r in self:
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
            date_order = pytz.utc.localize(r.order_id.date_order).astimezone(user_tz)
            r.expire_change_refund_date = date_order.date() + timedelta(days=r.product_id.number_days_change_refund)

    @api.depends('qty', 'refunded_qty')
    def _compute_quantity_canbe_refund(self):
        for r in self:
            r.quantity_canbe_refund = r.qty - r.refunded_qty

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        money_is_reduced = orderline.money_is_reduced
        if orderline.refunded_qty and orderline.qty > 0:
            money_is_reduced = (money_is_reduced/orderline.qty) * (orderline.qty - orderline.refunded_qty)
        result['expire_change_refund_date'] = orderline.expire_change_refund_date
        result['quantity_canbe_refund'] = orderline.quantity_canbe_refund
        result['reason_refund_id'] = orderline.reason_refund_id
        result['money_is_reduced'] = money_is_reduced
        result['money_point_is_reduced'] = orderline.money_point_is_reduced
        result['is_voucher_conditional'] = orderline.is_voucher_conditional
        result['is_product_defective'] = orderline.is_product_defective
        result['money_reduce_from_product_defective'] = orderline.money_reduce_from_product_defective
        return result
