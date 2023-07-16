# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_rank = fields.Boolean('Is Rank', default=False)
    card_rank_program_id = fields.Many2one('member.card', 'Card Rank Program', ondelete='restrict')
    order_status_format = fields.Boolean('Order Status Format')
    order_status_tokyolife = fields.Boolean('Order Status Tokyolife')
    plus_point_coefficient = fields.Integer('Plus Point Coefficient', compute='_compute_plus_point', store=True)

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        self.update_partner_card_rank()
        return res

    def update_partner_card_rank(self):
        member_cards = self.env['member.card'].get_member_card_by_date(self.date_order, self.config_id.store_id.brand_id.id)
        if not member_cards:
            return False
        is_rank = False
        partner_card_rank = self.partner_id.card_rank_ids.filtered(lambda f: f.brand_id == self.config_id.store_id.brand_id)
        if partner_card_rank:
            new_rank = partner_card_rank.card_rank_id
            for program in member_cards:
                if self.partner_id.group_id.id == program.customer_group_id.id and \
                        (self.partner_id.retail_type_ids and any(retail_type in program.partner_retail_ids for retail_type in self.partner_id.retail_type_ids)):
                    is_rank = True
                    value_to_upper_order = sum([payment_method.amount for payment_method in self.payment_ids if payment_method.payment_method_id.id in program.payment_method_ids.ids])
                    total_value_to_up = value_to_upper_order + sum(partner_card_rank.line_ids.filtered(lambda f: f.order_date >= (self.date_order - timedelta(days=program.time_set_rank))).mapped('value_to_upper'))
                    if new_rank.priority >= program.card_rank_id.priority:
                        self.update_status_card_rank(partner_card_rank)
                        self.create_partner_card_rank_detail(partner_card_rank.id, value_to_upper_order, new_rank.id, new_rank.id, total_value_to_up, program.id)
                        break
                    else:
                        if total_value_to_up >= program.min_turnover:
                            self.update_status_card_rank(partner_card_rank)
                            self.create_partner_card_rank_detail(partner_card_rank.id, value_to_upper_order, new_rank.id, program.card_rank_id.id, total_value_to_up, program.id)
                            break
        else:
            for program in member_cards:
                if self.partner_id.group_id.id == program.customer_group_id.id and \
                        (self.partner_id.retail_type_ids and any(retail_type in program.partner_retail_ids for retail_type in self.partner_id.retail_type_ids)):
                    is_rank = True
                    value_to_upper_order = sum([payment_method.amount for payment_method in self.payment_ids if payment_method.payment_method_id.id in program.payment_method_ids.ids])
                    if value_to_upper_order >= program.min_turnover:
                        self.create_partner_card_rank(value_to_upper_order, program.id, program.card_rank_id.id)
                        break
        if is_rank:
            self.sudo().write({'is_rank': True})

    def create_partner_card_rank(self, value_to_upper_order, program_id, rank_id):
        res = self.env['partner.card.rank'].sudo().create({
            'customer_id': self.partner_id.id,
            'brand_id': self.config_id.store_id.brand_id.id,
            'line_ids': [(0, 0, {
                'order_id': self.id,
                'order_date': self.date_order,
                'real_date': self.create_date,
                'value_orders': self.amount_total,
                'value_to_upper': value_to_upper_order,
                'old_card_rank_id': rank_id,
                'new_card_rank_id': rank_id,
                'value_up_rank': 0,
                'program_cr_id': program_id,
                'status': True
            })]
        })
        return res

    def update_status_card_rank(self, partner_card_rank_id):
        PartnerCardRankLine = self.env['partner.card.rank.line'].sudo()
        partner_card_rank_line_ids = PartnerCardRankLine.search(
            [('partner_card_rank_id', '=', partner_card_rank_id.id), ('status', '=', True)])
        if partner_card_rank_line_ids:
            for partner_card_rank_line_id in partner_card_rank_line_ids:
                partner_card_rank_line_id.write({
                    'status': False
                })
    def create_partner_card_rank_detail(self, partner_card_rank_id, value_to_upper, old_rank_id, new_rank_id,
                                        total_value_to_up, program_id):
         self.env['partner.card.rank.line'].sudo().create({
            'partner_card_rank_id': partner_card_rank_id,
            'order_id': self.id,
            'order_date': self.date_order,
            'real_date': self.create_date,
            'value_orders': self.amount_total,
            'value_to_upper': value_to_upper,
            'old_card_rank_id': old_rank_id,
            'new_card_rank_id': new_rank_id,
            'value_up_rank': total_value_to_up if old_rank_id != new_rank_id else 0,
            'program_cr_id': program_id,
            'status': True if old_rank_id != new_rank_id else False
        })

    @api.model
    def _order_fields(self, ui_order):
        res = super()._order_fields(ui_order)
        if 'card_rank_program_id' not in res and ui_order.get('card_rank_program'):
            res.update({'card_rank_program_id': ui_order.get('card_rank_program', {}).get('id')})
        if ui_order.get('order_status_format'):
            res.update({
                'order_status_format': ui_order.get('order_status_format') or False,
            })
        if ui_order.get('order_status_tokyolife'):
            res.update({
                'order_status_tokyolife': ui_order.get('order_status_tokyolife') or False,
            })

        return res

    # @api.model
    # def _process_order(self, order, draft, existing_order):
    #     pos_id = super(PosOrder, self)._process_order(order, draft, existing_order)
    #     HistoryPoint = self.env['partner.history.point']
    #     if not existing_order:
    #         pos = self.env['pos.order'].browse(pos_id)
    #         store = pos._get_store_brand_from_program()
    #         if store is not None:
    #             history_values = pos._prepare_history_point_coefficient_value(store, pos.plus_point_coefficient + sum(
    #                                                                              [x.plus_point_coefficient for x in
    #                                                                               pos.lines]))
    #             HistoryPoint.sudo().create(history_values)
    #             pos.partner_id._compute_reset_day(pos.date_order, pos.program_store_point_id.point_expiration,
    #                                               store)
    #     return pos_id
    
    def _prepare_history_point_value(self, store: str, point_type='new', reason='', points_used=0, points_back=0):
        vals = super()._prepare_history_point_value(store, point_type='new', reason='', points_used=0, points_back=0)
        pos = self
        vals['points_coefficient'] = (pos.plus_point_coefficient + sum([x.plus_point_coefficient for x in pos.lines]))
        vals['points_store'] += (pos.plus_point_coefficient + sum([x.plus_point_coefficient for x in pos.lines]))
        return vals

    @api.depends('program_store_point_id')
    def _compute_plus_point(self):
        for item in self:
            item.plus_point_coefficient = 0
            total = 0
            pos_session = item.session_id
            brand_id = pos_session.config_id.store_id.brand_id

            if (item.order_status_format and brand_id.code == 'FMT') or (
                    item.order_status_tokyolife and brand_id.code == 'TKL'):
                member_card_ids = self.env['member.card'].get_member_card_by_date(item.date_order, brand_id.id)
                card_rank_line_ids = item.partner_id.card_rank_ids.mapped('line_ids').sorted(lambda x: (x.real_date, x.id), reverse=True)
                if card_rank_line_ids:
                    card_rank_line_id = card_rank_line_ids[0]
                    member_card_id = member_card_ids.filtered(lambda x: x.card_rank_id == card_rank_line_id.old_card_rank_id)
                    if member_card_id:
                        if member_card_id.retail_type_not_apply_ids:
                            if any(x.id in member_card_id.retail_type_not_apply_ids.ids for x in item.partner_id.retail_type_ids):
                                return
                        point_coefficient_first_order = member_card_id.point_coefficient_first_order
                        point_plus_first_order = member_card_id.point_plus_first_order
                        if item.program_store_point_id:
                            if point_coefficient_first_order > 0:
                                total += ((point_coefficient_first_order - 1) * item.point_order + (
                                        point_coefficient_first_order - 1) * item.point_event_order)
                            if point_plus_first_order > 0:
                                total += point_plus_first_order
            item.plus_point_coefficient = total

    @api.depends('plus_point_coefficient')
    def _compute_total_point(self):
        super()._compute_total_point()
        for order in self:
            order.total_point += (order.plus_point_coefficient + sum([x.plus_point_coefficient for x in order.lines]))

    def _prepare_history_point_coefficient_value(self, store, points_coefficient, point_type='coefficient', reason=''):
        return {
            'partner_id': self.partner_id.id,
            'store': store,
            'pos_order_id': self.id,
            'date_order': self.date_order,
            'points_coefficient': points_coefficient,
            'point_order_type': point_type,
            'reason': reason or self.name or '',
            'points_store': points_coefficient
        }

    def get_point_order(self, money_value, brand_id, is_purchased):
        current_rank_of_customer = (self.partner_id.card_rank_by_brand or {}).get(str(brand_id))
        program = self.program_store_point_id
        if self.allow_for_point and (self.config_id.store_id.id in program.store_ids.ids or not program.store_ids) and current_rank_of_customer and program.card_rank_active:
            accumulate_by_rank = program.accumulate_by_rank_ids.filtered(lambda x: x.card_rank_id.id == current_rank_of_customer[0])
            coefficient = 1 if is_purchased else (accumulate_by_rank.coefficient or 1)
            if accumulate_by_rank:
                return int(int((money_value * accumulate_by_rank.accumulative_rate / 100) * (program.card_rank_point_addition / program.card_rank_value_convert)) * coefficient)
        return super().get_point_order(money_value, brand_id, is_purchased)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    card_rank_applied = fields.Boolean('Card Rank Applied', default=False)
    card_rank_discount = fields.Float('Card Rank Discount', default=0)

    plus_point_coefficient = fields.Integer('Plus Point Coefficient', compute='_compute_plus_point', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for idx, line in enumerate(vals_list):
            if line.get('card_rank_discount') and line.get('card_rank_applied'):
                vals_list[idx]['discount_details_lines'] = line.get('discount_details_lines', []) + [
                    (0, 0, {
                        'type': 'card',
                        'listed_price': line['price_unit'],
                        'recipe': line['card_rank_discount'],
                    })
                ]
        return super(PosOrderLine, self).create(vals_list)

    @api.depends('order_id.program_store_point_id')
    def _compute_plus_point(self):
        for item in self:
            item.plus_point_coefficient = 0
            total = 0
            pos_session = item.order_id.session_id
            brand_id = pos_session.config_id.store_id.brand_id

            if (item.order_id.order_status_format and brand_id.code == 'FMT') or (
                    item.order_id.order_status_tokyolife and brand_id.code == 'TKL'):
                member_card_ids = self.env['member.card'].get_member_card_by_date(item.order_id.date_order, brand_id.id)
                card_rank_line_ids = item.order_id.partner_id.card_rank_ids.mapped('line_ids').sorted(lambda x: (x.real_date, x.id), reverse=True)
                if card_rank_line_ids:
                    card_rank_line_id = card_rank_line_ids[0]
                    member_card_id = member_card_ids.filtered(lambda x: x.card_rank_id == card_rank_line_id.old_card_rank_id)
                    if member_card_id:
                        if member_card_id.retail_type_not_apply_ids:
                            if any(x.id in member_card_id.retail_type_not_apply_ids.ids for x in item.order_id.partner_id.retail_type_ids):
                                return
                        point_coefficient_first_order = member_card_id.point_coefficient_first_order
                        if item.order_id.program_store_point_id:
                            total += ((point_coefficient_first_order - 1) * item.point_addition + (
                                    point_coefficient_first_order - 1) * item.point_addition_event) if point_coefficient_first_order > 0 else 0
            item.plus_point_coefficient = total
