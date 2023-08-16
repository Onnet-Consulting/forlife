# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta
from odoo.osv.expression import AND
from dateutil.relativedelta import relativedelta
import math


class PosOrder(models.Model):
    _inherit = 'pos.order'

    brand_id = fields.Many2one('res.brand', string='Brand')
    approved = fields.Boolean('Approved', default=False, copy=False)
    is_refund_order = fields.Boolean('Is Refund Order', copy=False, default=False)
    is_change_order = fields.Boolean('Is Change Order', copy=False, default=False)
    refund_point = fields.Integer('Refund Point', compute="_compute_refund_point", store=True)
    pay_point = fields.Integer('Pay Point', compute="_compute_pay_point", store=True)
    voucher_id = fields.Many2one('voucher.voucher', string='Voucher Exchange', copy=False)

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
        default_domain = [('brand_id', '=', brand_id), ('config_id.store_id', '=', store_id.id), '!', '|',
                          ('state', '=', 'draft'), ('state', '=', 'cancelled')]
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
        # if order['data']['is_refund_product']:
        #     for l in order['data']['lines']:
        #         if l[2]['price_subtotal_incl_refund']:
        #             l[2]['price_subtotal_incl'] = l[2]['price_subtotal_incl_refund']
        #         if l[2]['price_subtotal_incl_refund']:
        #             l[2]['price_unit'] = l[2]['price_unit_refund']
        for l in order['data']['lines']:
            if l[2]['money_reduce_from_product_defective'] >0:
                l[2]['price_subtotal'] = l[2]['price_subtotal'] - l[2]['money_reduce_from_product_defective']
                l[2]['price_unit'] = l[2]['price_unit'] - l[2]['money_reduce_from_product_defective']
            if l[2]['handle_change_refund_price'] > 0:
                l[2]['discount_details_lines'] = [(0, 0, {
                    'type': 'change_refund',
                    'recipe': -l[2]['handle_change_refund_price']
                })]
        pos_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        HistoryPoint = self.env['partner.history.point']
        Voucher = self.env['voucher.voucher']
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
            for p in pos.lines:
                if p.product_defective_id:
                    p.product_defective_id.is_already_in_use = True
                    p.product_defective_id.quantity_can_be_sale = p.product_defective_id.quantity_can_be_sale - p.qty
            # update history back order
            if pos.refund_point > 0 or pos.pay_point > 0:
                if pos.partner_id.is_member_app_format or pos.partner_id.is_member_app_forlife:
                    store = pos._get_store_brand_from_program()
                    if store is not None:
                        history_values = pos._prepare_history_point_back_order_value(store, points_back=pos.pay_point)
                        HistoryPoint.sudo().create(history_values)
                        if pos.program_store_point_id:
                            pos.partner_id._compute_reset_day(pos.date_order, pos.program_store_point_id.point_expiration,
                                                              store)

        # create voucher
        line_voucher_id = pos.lines.filtered(lambda x: x.product_id.is_voucher_auto)
        if line_voucher_id:
            program_voucher_id = line_voucher_id[0].product_id.program_voucher_id
            price = line_voucher_id[0].price_unit
            partner = pos.partner_id

            # search program voucher

            if program_voucher_id:
                val_voucher = self._prepare_voucher(program_voucher_id, price, partner)
                if val_voucher:
                    voucher_id = Voucher.create(val_voucher)
                    pos.write({
                        'voucher_id': voucher_id.id if voucher_id else False
                    })
        return pos.id

    @api.model
    def _order_fields(self, ui_order):
        values = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get('is_change_product') or ui_order.get('is_refund_product'):
            values.update({
                'approved': ui_order['approved'] or False,
            })
            if ui_order.get('is_change_product'):
                values.update({
                    'is_change_order': ui_order.get('is_change_product') or False,
                })
            if ui_order.get('is_refund_product'):
                values.update({
                    'is_refund_order': ui_order.get('is_refund_product') or False,
                })
        return values

    @api.depends('lines.refunded_orderline_id', 'is_refund_order')
    def _compute_refund_point(self):
        for item in self:
            item.refund_point = 0
            total = 0
            if item.is_refund_order:
                for line in item.lines:
                    qty_refund = abs(line.qty)
                    for discount_line in line.refunded_orderline_id.discount_details_lines.filtered(
                            lambda x: x.type == 'point'):
                        total += (discount_line.recipe / line.refunded_orderline_id.qty) * qty_refund
            item.refund_point = total

    @api.depends('lines.refunded_orderline_id', 'refunded_order_ids')
    def _compute_pay_point(self):
        """
            total_order_point -> A = Tổng điểm (điểm cộng đơn + điểm cộng sự kiện + điểm cộng hệ số) - Đơn gốc
            order_point -> X = (Tổng tiền line không có điểm cộng đơn trả/ Tổng tiền line không có điểm cộng đơn gốc) * A
            product_point -> Y = Tổng điểm (điểm cộng đơn + điểm cộng sự kiện + điểm cộng hệ số) ở tất cả line
            pay_point -> Z = X + Y
        """
        for item in self:
            pay_point = 0
            old_orders = item.refunded_order_ids
            if not old_orders:
                return
            partner_id = old_orders[0].partner_id
            store = item._get_store_brand_from_program()
            history_tmp_points = partner_id.history_points_forlife_ids
            if store == 'format':
                history_tmp_points = partner_id.history_points_format_ids
            history_points = history_tmp_points.filtered(lambda x: x.point_order_type == 'reset_order')
            if (history_points and history_points[0].date_order < old_orders[0].date_order) or not history_points:
                origin_order_id = item.lines.refunded_orderline_id.mapped('order_id')
                order_point = 0
                product_point = 0
                if origin_order_id:
                    # Điểm đơn hàng gốc = Tổng điểm (điểm cộng đơn + điểm cộng sự kiện + điểm cộng hệ số)
                    total_order_point = origin_order_id.point_order + origin_order_id.point_event_order + origin_order_id.plus_point_coefficient
                    if total_order_point > 0:
                        # Lấy toàn bộ line k có điểm của đơn gốc
                        origin_lines_not_points = origin_order_id.lines.filtered(lambda x: not x.point_addition and not x.point_addition_event and not x.plus_point_coefficient and not x.is_promotion)
                        subtotal_paid_origin = sum(origin_lines_not_points.mapped('subtotal_paid'))
                        if subtotal_paid_origin:
                            # Lấy toàn bộ line k có điểm cộng của đơn trả
                            lines_not_points = item.lines.filtered(lambda x: x.refunded_orderline_id and (not x.refunded_orderline_id.point_addition and not x.refunded_orderline_id.point_addition_event and not x.refunded_orderline_id.plus_point_coefficient and not x.is_promotion))
                            subtotal_paid_line = abs(sum(lines_not_points.mapped('subtotal_paid')))
                            order_point = 0 if subtotal_paid_line == 0 else math.floor((subtotal_paid_line/subtotal_paid_origin) * total_order_point)

                    # Tính điểm trả sản phẩm vào trường pay_point_line
                    # Điểm trả sản phẩm = (SL trả/ SL gốc) * Tổng điểm (điểm cộng đơn + điểm cộng sự kiện + điểm cộng hệ số) ở line gốc
                    for line in item.lines.filtered(lambda x: x.refunded_orderline_id and x.qty and not x.is_promotion):
                        origin_line = line.refunded_orderline_id
                        # Tổng điểm cộng line gốc
                        line_origin_point = origin_line.point_addition + origin_line.point_addition_event + origin_line.plus_point_coefficient
                        # (SL trả/ SL gốc) * Tổng điểm cộng line gốc
                        pay_point_line = math.floor(abs(line.qty)/origin_line.qty * line_origin_point)
                        line.pay_point_line = pay_point_line
                        product_point += pay_point_line

                pay_point = order_point + product_point
            item.pay_point = pay_point

            """ Logic cũ tạm thời comment """
            # # lấy chương trình tích điểm
            # points_promotion = old_orders.mapped('program_store_point_id')
            # if not points_promotion:
            #     return
            # points_promotion = points_promotion[0]
            #
            # lines_detail_event_points = item.lines.filtered(lambda x: x.refunded_orderline_id and (
            #         x.refunded_orderline_id.point_addition > 0 or x.refunded_orderline_id.point_addition_event > 0))
            # for line in lines_detail_event_points:
            #     if line.qty < 0:
            #         # chi tiết đơn hàng gốc
            #         old_ol = line.refunded_orderline_id
            #         # sl gốc
            #         old_qty = old_ol.qty
            #         # sl trả hiện tại
            #         current_qty = abs(line.qty)
            #         point_product += (((old_ol.point_addition + old_ol.point_addition_event) * current_qty) / old_qty) if old_qty else 0
            #
            # # lấy các line mà đơn gốc line ko có điểm trên từng column
            # lines_detail_points = item.lines.filtered(lambda x: x.refunded_orderline_id)
            # if lines_detail_event_points:
            #     lines_detail_points = item.lines.filtered(
            #         lambda x: x.refunded_orderline_id and (x.id not in lines_detail_event_points.ids))
            # # lấy giá trị quy đổi của chương trình dựa trên 1 điểm
            # coefficient = points_promotion.value_conversion / points_promotion.point_addition if points_promotion.point_addition else 0
            # if coefficient:
            #     total_point_order = 0
            #     for line_1 in lines_detail_points:
            #         if line_1.qty < 0:
            #             # sl trả hiện tại
            #             current_qty_1 = abs(line_1.qty)
            #             total_point_order += line_1.price_unit * current_qty_1
            #     point_order += total_point_order // coefficient
            #
            # # tính point nếu có sự kiện diễn ra
            # total_point_event_order = 0
            # if old_orders[0].point_event_order > 0:
            #     # lấy giá trị quy đổi của chương trình sự kiện
            #     point_event_promotion = points_promotion.event_ids.filtered(
            #         lambda x: x.from_date <= old_orders[0].date_order and x.to_date >= old_orders[0].date_order)
            #     if point_event_promotion:
            #         coefficient_event = point_event_promotion[0].value_conversion / point_event_promotion[
            #             0].point_addition if point_event_promotion[0].point_addition else 0
            #         if coefficient_event:
            #             for line_2 in lines_detail_points:
            #                 if line_2.qty < 0:
            #                     # sl trả hiện tại
            #                     current_qty_2 = abs(line_2.qty)
            #                     total_point_event_order += line_2.price_unit * current_qty_2
            #             point_event_order += total_point_event_order // coefficient_event


    def _prepare_history_point_back_order_value(self, store, point_type='back_order', reason='', points_used=0,
                                                points_back=0):
        self.ensure_one()
        pos = self

        return {
            'partner_id': pos.partner_id.id,
            'store': store,
            'pos_order_id': pos.id,
            'date_order': pos.date_order,
            'points_fl_order': self.refund_point,
            'point_order_type': point_type,
            'reason': reason or pos.name or '',
            'points_used': abs(sum([line.point / 1000 for line in pos.lines])),  # go back to edit
            'points_back': points_back,
            'points_store': pos.point_order + self.refund_point + pos.point_event_order + sum(
                [x.point_addition for x in pos.lines]) + sum(
                [x.point_addition_event for x in pos.lines]) - abs(
                sum([line.point / 1000 for line in pos.lines])) - points_back
        }

    def _prepare_voucher(self, program_voucher_id, price, partner):
        vals = {
            'program_voucher_id': program_voucher_id.id,
            'type': program_voucher_id.type,
            'brand_id': program_voucher_id.brand_id.id,
            'store_ids': [(6, False, program_voucher_id.store_ids.ids)],
            'start_date': program_voucher_id.start_date,
            'state': 'sold',
            'partner_id': partner.id,
            'price': price,
            'price_used': 0,
            'price_residual': price - 0,
            'derpartment_id': program_voucher_id.derpartment_id.id,
            'end_date': program_voucher_id.end_date,
            'apply_many_times': program_voucher_id.apply_many_times,
            'apply_contemp_time': program_voucher_id.apply_contemp_time,
            'product_voucher_id': program_voucher_id.product_id.id,
            'purpose_id': program_voucher_id.purpose_id.id,
            'product_apply_ids': [(6, False, program_voucher_id.product_apply_ids.ids)],
            'is_full_price_applies': program_voucher_id.is_full_price_applies,
            'using_limit': program_voucher_id.using_limit
        }
        return vals
