# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


class PointCompensateRequest(models.Model):
    _name = 'point.compensate.request'
    _description = 'Point Compensate Request'

    order_id = fields.Many2one('pos.order', required=True)
    compensated = fields.Boolean(string='Compensated', default=False)
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True)
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('unique_order', 'UNIQUE(order_id)', _('Order must be unique!'))
    ]

    def action_point_compensate(self):
        point_promotions = self.env['points.promotion'].search(
            [('state', '=', 'in_progress'), ('from_date', '<=', fields.Datetime.now()), ('to_date', '>=', fields.Datetime.now())])
        pc_requests = self.search([('order_id.brand_id', 'in', point_promotions.brand_id.ids), ('compensated', '=', False)])
        for promo in point_promotions:
            store = 'forlife' if promo.brand_id.code == 'TKL' else 'format'
            can_compensate = pc_requests.filtered(
                lambda f: f.order_id.brand_id == promo.brand_id and (f.order_id.date_order + relativedelta(days=promo.point_compensate_time)) >= f.create_date)
            for o in can_compensate:
                total_amount = sum(o.order_id.payment_ids.filtered(lambda p: p.payment_method_id.id in promo.payment_method_ids.ids).mapped('amount'))
                point_compensate = int(total_amount * promo.point_compensate_rate / 100000)
                if point_compensate > 0:
                    o.order_id.write({
                        'point_order': point_compensate,
                        'program_store_point_id': promo.id,
                    })
                    history_values = self._prepare_history_point_value(o.order_id, point_compensate, store)
                    self.env['partner.history.point'].sudo().create(history_values)
                    o.order_id.partner_id._compute_reset_day(o.order_id.date_order, promo.point_expiration, store)
                    o.order_id.action_point_addition()
            inactive_lst = pc_requests.filtered(
                lambda f: f.order_id.brand_id == promo.brand_id and (f.order_id.date_order + relativedelta(days=promo.point_compensate_time)) < f.create_date)
            if can_compensate:
                can_compensate.write({'compensated': True})
            if inactive_lst:
                inactive_lst.write({'active': False})

    def _prepare_history_point_value(self, order, point, store):
        return {
            'partner_id': order.partner_id.id,
            'store': store,
            'pos_order_id': order.id,
            'date_order': order.date_order,
            'points_fl_order': point,
            'point_order_type': 'point compensate',
            'reason': order.name,
            'points_used': 0,
            'points_back': 0,
            'points_store': point
        }


