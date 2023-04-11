# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta
from odoo.osv.expression import AND
from dateutil.relativedelta import relativedelta


class PosOrder(models.Model):
    _inherit = 'pos.order'

    brand_id = fields.Many2one('res.brand', string='Brand')
    approved = fields.Boolean('Approved', default=False, copy=False)
    # is_refund_order = fields.Boolean('Is Refund Order', copy=False, default=False)
    # is_change_order = fields.Boolean('Is Change Order', copy=False, default=False)
    refund_point = fields.Integer('Refund Point', compute="_compute_refund_point")
    pay_point = fields.Integer('Pay Point', compute="_compute_pay_point")

    @api.model
    def search_change_order_ids(self, config_id, brand_id, store_id, domain, limit, offset, search_details):
        """Search for all orders that satisfy the given domain, limit and offset."""
        store_id = self.env['store'].sudo().search([('id', '=', store_id)], limit=1)
        default_domain = [('brand_id', '=', brand_id), '!', '|', ('state', '=', 'draft'), ('state', '=', 'cancelled')]
        if store_id.number_month != 0 and search_details.get('fieldName', False) == 'PHONE':
            start_date = fields.Date.today() - relativedelta(months=store_id.number_month)
            end_date = fields.Date.today()
            default_domain = [('date_order', '>=', start_date), ('date_order', '<=', end_date)] + default_domain

        real_domain = AND([domain, default_domain])
        ids = self.search(AND([domain, default_domain]), limit=limit, offset=offset).ids
        totalCount = self.search_count(real_domain)
        return {'ids': ids, 'totalCount': totalCount}

    @api.model
    def search_refund_order_ids(self, config_id, brand_id, store_id, domain, limit, offset, search_details):
        """Search for all orders that satisfy the given domain, limit and offset."""
        store_id = self.env['store'].sudo().search([('id', '=', store_id)], limit=1)
        default_domain = [('brand_id', '=', brand_id), ('config_id.store_id', '=', store_id.id), '!', '|', ('state', '=', 'draft'), ('state', '=', 'cancelled')]
        if store_id.number_month != 0 and search_details.get('fieldName', False) == 'PHONE':
            start_date = fields.Date.today() - relativedelta(months=store_id.number_month)
            end_date = fields.Date.today()
            default_domain = [('date_order', '>=', start_date), ('date_order', '<=', end_date)] + default_domain

        real_domain = AND([domain, default_domain])
        ids = self.search(AND([domain, default_domain]), limit=limit, offset=offset).ids
        totalCount = self.search_count(real_domain)
        return {'ids': ids, 'totalCount': totalCount}

    # Update brand in POS Order
    @api.model
    def _process_order(self, order, draft, existing_order):
        pos_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        HistoryPoint = self.env['partner.history.point']
        if pos_id:
            order = order['data']
            pos_session = self.env['pos.session'].browse(order['pos_session_id'])
            brand_id = pos_session.config_id.store_id.brand_id
            pos = False
            if not existing_order:
                pos = self.env['pos.order'].browse(pos_id)
            else:
                pos = existing_order
            for pos_order_id in pos:
                if pos_order_id.brand_id.id != brand_id.id:
                    pos_order_id.brand_id = brand_id

        #     update history back order
            if pos.refund_point > 0 or pos.pay_point > 0:
                if pos.partner_id.is_member_app_format or pos.partner_id.is_member_app_forlife:
                    if not pos.program_store_point_id:
                        return pos.id
                    store = pos._get_store_brand_from_program()
                    if store is not None:
                        history_values = pos._prepare_history_point_back_order_value(store, points_back=pos.pay_point)
                        HistoryPoint.sudo().create(history_values)
                        pos.partner_id._compute_reset_day(pos.date_order, pos.program_store_point_id.point_expiration, store)
        return pos.id

    @api.model
    def _order_fields(self, ui_order):
        values = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get('is_change_product') or ui_order.get('is_refund_product'):
            values.update({
                'approved': ui_order['approved'] or False,
            })
        return values

    @api.depends('lines.refunded_orderline_id', 'lines.qty')
    def _compute_refund_point(self):
        for item in self:
            item.refund_point = 0
            total = 0
            for line in item.lines:
                qty_refund = abs(line.qty)
                for discount_line in line.refunded_orderline_id.discount_details_lines.filtered(lambda x: x.type == 'point'):
                    total += (discount_line.recipe/line.refunded_orderline_id.qty) * qty_refund
            item.refund_point = total

    @api.depends('lines.refunded_orderline_id')
    def _compute_pay_point(self):
        for item in self:
            item.pay_point = 0
            point_product = 0
            point_order = 0

            old_orders = item.refunded_order_ids
            if not old_orders:
                return
            partner_id = old_orders[0].partner_id
            store = item._get_store_brand_from_program()
            history_tmp_points = partner_id.history_points_forlife_ids
            if store == 'format':
                history_tmp_points = partner_id.history_points_format_ids
            history_points = history_tmp_points.filtered(lambda x: x.point_order_type == 'reset_order')
            if history_points and history_points[0].date_order < old_orders[0].date_order:
                points_promotion = old_orders.mapped('program_store_point_id')
                if not points_promotion:
                    return
                points_promotion = points_promotion[0]
                coefficient = points_promotion.value_conversion / points_promotion.point_addition
                for line in item.lines:
                    if line.refunded_orderline_id:
                        old_orderline = line.refunded_orderline_id
                        old_qty = old_orderline.qty
                        current_qty = abs(line.qty)
                        if old_orderline.point_addition > 0 or old_orderline.point_addition_event > 0:
                            point_product += ((old_orderline.point_addition + old_orderline.point_addition_event) * current_qty) / old_qty
                        else:
                            point_order += line.price_unit * current_qty
                if coefficient:
                    point_order = point_order / coefficient
            item.pay_point = point_product + point_order


    def _prepare_history_point_back_order_value(self, store, point_type='back_order', reason='', points_used=0, points_back=0):
        self.ensure_one()
        pos = self

        return {
            'partner_id': pos.partner_id.id,
            'store': store,
            'pos_order_id': pos.id,
            'date_order': pos.date_order,
            'points_fl_order':self.refund_point,
            'point_order_type': point_type,
            'reason': reason or pos.name or '',
            'points_used': abs(sum([line.point / 1000 for line in pos.lines])),  # go back to edit
            'points_back': points_back,
            'points_store': pos.point_order + self.refund_point + pos.point_event_order + sum([x.point_addition for x in pos.lines]) + sum(
                [x.point_addition_event for x in pos.lines]) - abs(sum([line.point / 1000 for line in pos.lines])) - points_back
        }


