from odoo import api, fields, models, _
from datetime import datetime
import pytz
from ast import literal_eval
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PosOrder(models.Model):
    _inherit = 'pos.order'

    point_order = fields.Integer('Point Order', compute='_compute_point_order', store=True)
    point_event_order = fields.Integer('Point event Order', compute='_compute_point_order', store=True)
    total_point = fields.Integer('Total Point', readonly=True, compute='_compute_total_point', store=True,
                                 help='Điểm cộng đơn hàng + Điểm sự kiện đơn + Điểm cộng + Điểm sự kiện')
    item_total_point = fields.Integer(
        'Item Point Total', readonly=True, compute='_compute_item_total_point', store=True,
        help='Includes the total of product point and product event point')
    program_store_point_id = fields.Many2one('points.promotion', 'Program Store Point')
    allow_compensate_point = fields.Boolean(compute='_allow_compensate_point', store=True)
    point_addition_move_ids = fields.Many2many(
        'account.move', 'pos_order_account_move_point_addition', string='Point Addition Move', readonly=True)
    total_order_line_point_used = fields.Integer()
    total_order_line_redisual = fields.Integer()
    allow_for_point = fields.Boolean()

    @api.depends('lines', 'lines.point_addition', 'lines.point_addition_event')
    def _compute_item_total_point(self):
        for order in self:
            order.item_total_point = sum(order.mapped('lines.point_addition')) + sum(order.mapped('lines.point_addition_event'))

    @api.depends('item_total_point', 'point_order', 'point_event_order')
    def _compute_total_point(self):
        for order in self:
            order.total_point = order.point_order + order.point_event_order + order.item_total_point

    @api.depends('program_store_point_id', 'total_point')
    def _allow_compensate_point(self):
        for order in self:
            order.allow_compensate_point = not bool(order.program_store_point_id and order.total_point >= 0)

    @api.model
    def _process_order(self, order, draft, existing_order):
        pos_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        HistoryPoint = self.env['partner.history.point']
        if not existing_order:
            pos = self.env['pos.order'].browse(pos_id)
            store = pos._get_store_brand_from_program()
            brand_pos_id = pos.config_id.store_id.brand_id.id
            if brand_pos_id == self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id \
                    and not pos.partner_id.is_purchased_of_format and pos.program_store_point_id and store:
                pos.partner_id.is_purchased_of_format = True
            if brand_pos_id == self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id \
                    and not pos.partner_id.is_purchased_of_forlife and pos.program_store_point_id and store:
                pos.partner_id.is_purchased_of_forlife = True
            if pos.program_store_point_id:
                if store is not None:
                    history_values = pos._prepare_history_point_value(store)
                    HistoryPoint.sudo().create(history_values)
                    pos.partner_id._compute_reset_day(pos.date_order, pos.program_store_point_id.point_expiration, store)
                    pos.action_point_addition()
        return pos_id

    def btn_compensate_points_all(self, reason):
        for order in self.filtered(lambda x: x.allow_compensate_point):
            order._compensate_points(reason)

    def _compensate_points(self, reason):
        pos_order = self
        if not pos_order.partner_id.is_member_app_format and not pos_order.partner_id.is_member_app_forlife:
            return
        if not pos_order.program_store_point_id:
            program = self.get_program_promotion({
                'date_order': datetime.strftime(pos_order.date_order, DEFAULT_SERVER_DATETIME_FORMAT),
                'session_id': pos_order.session_id.id
            })
            if not program:
                return
            pos_order.program_store_point_id = program.id
        store = pos_order._get_store_brand_from_program()
        if store:
            history_values = pos_order._prepare_history_point_value(store, point_type='point compensate', reason=reason)
            self.env['partner.history.point'].sudo().create(history_values)
            pos_order.partner_id._compute_reset_day(pos_order.date_order, pos_order.program_store_point_id.point_expiration, store)
            pos_order.action_point_addition()

    is_check_allow_compensate_point = fields.Boolean(compute='_compute_check_pos_order_compensate_point')

    @api.depends('partner_id','config_id.store_id.brand_id')
    def _compute_check_pos_order_compensate_point(self):
        for pos_order in self:
            program = self.get_program_promotion({
                'date_order': datetime.strftime(pos_order.date_order, DEFAULT_SERVER_DATETIME_FORMAT),
                'session_id': pos_order.session_id.id
            })
            brand_pos_id = pos_order.config_id.store_id.brand_id.id
            if not pos_order.partner_id:
                pos_order.is_check_allow_compensate_point = False
            elif (brand_pos_id == self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id and self.env.ref(
                    'forlife_pos_app_member.res_partner_retail_format_app', raise_if_not_found=False).id not in pos_order.partner_id.retail_type_ids.ids) or (
                    brand_pos_id == self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id and self.env.ref(
                'forlife_pos_app_member.res_partner_retail_tokyolife_app', raise_if_not_found=False).id not in pos_order.partner_id.retail_type_ids.ids):
                pos_order.is_check_allow_compensate_point = False
            elif not pos_order.allow_compensate_point:
                pos_order.is_check_allow_compensate_point = False
            elif not program and not pos_order.program_store_point_id:
                pos_order.is_check_allow_compensate_point = False
            else:
                pos_order.is_check_allow_compensate_point = True

    def check_pos_order_compensate_point(self):
        for pos_order in self:
            program = self.get_program_promotion({
                'date_order': datetime.strftime(pos_order.date_order, DEFAULT_SERVER_DATETIME_FORMAT),
                'session_id': pos_order.session_id.id
            })
            brand_pos_id = pos_order.config_id.store_id.brand_id.id
            if not pos_order.partner_id:
                raise UserError(_('Đơn hàng này chưa chọn khách hàng !'))
            elif (brand_pos_id == self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id and self.env.ref(
                    'forlife_pos_app_member.res_partner_retail_format_app', raise_if_not_found=False).id not in pos_order.partner_id.retail_type_ids.ids) or (
                    brand_pos_id == self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id and self.env.ref(
                'forlife_pos_app_member.res_partner_retail_tokyolife_app', raise_if_not_found=False).id not in pos_order.partner_id.retail_type_ids.ids):
                raise UserError(_('Khách hàng này chưa cài app!'))
            elif not pos_order.allow_compensate_point:
                raise UserError(_(f"Đơn hàng này đã được tích điểm"))
            elif not program and not pos_order.program_store_point_id:
                raise UserError(_('Đơn hàng không có chương trình tích điểm nào phù hợp!'))

    def check_pos_order_compensate_point_from_list(self):
        list_partner_empty = []
        list_partner_empty_app = []
        list_order_empty_app = []
        list_order_has_point = []
        list_order_no_program_points_order = []
        for pos_order in self:
            program = self.get_program_promotion({
                'date_order': datetime.strftime(pos_order.date_order, DEFAULT_SERVER_DATETIME_FORMAT),
                'session_id': pos_order.session_id.id
            })
            brand_pos_id = pos_order.config_id.store_id.brand_id.id
            if not pos_order.partner_id:
                list_partner_empty.append(pos_order.name)
            elif (brand_pos_id == self.env.ref('forlife_point_of_sale.brand_format',raise_if_not_found=False).id
                  and self.env.ref('forlife_pos_app_member.res_partner_retail_format_app',raise_if_not_found=False).id not in pos_order.partner_id.retail_type_ids.ids) \
                    or (brand_pos_id == self.env.ref('forlife_point_of_sale.brand_tokyolife',raise_if_not_found=False).id
                        and self.env.ref('forlife_pos_app_member.res_partner_retail_tokyolife_app', raise_if_not_found=False).id not in pos_order.partner_id.retail_type_ids.ids):
                list_partner_empty_app.append(pos_order.partner_id.name)
                list_order_empty_app.append(pos_order.name)
                # raise UserError(_('Khách hàng chưa cài app!'))
            elif not pos_order.allow_compensate_point:
                list_order_has_point.append(pos_order.name)
                # raise UserError(_(f"Đơn hàng này đã được tích điểm"))
            elif not program and not pos_order.program_store_point_id:
                list_order_no_program_points_order.append(pos_order.name)
        if list_partner_empty:
            raise UserError(_('Đơn hàng {} chưa chọn khách hàng !'.format(', '.join(list_order_has_point))))
        elif list_partner_empty_app:
            raise UserError(_('Khách hàng {} tại đơn hàng {} chưa cài app! !'.format(', '.join(list_partner_empty_app),', '.join(list_order_empty_app))))
        elif list_order_has_point:
            raise UserError(_('Đơn hàng {} đã được tích điểm!'.format(', '.join(list_order_has_point))))
        elif list_order_no_program_points_order:
            raise UserError(_('Đơn hàng {} không có chương trình tích điểm nào phù hợp!'.format(', '.join(list_order_no_program_points_order))))
        else:
            ctx = dict(self._context)
            view_id_form = self.env['ir.ui.view'].search([('name', '=', 'view.pos.compensate.point.order')])
            return {
                'name': _('Compensate Point'),
                'res_model': 'pos.compensate.point.order',
                'type': 'ir.actions.act_window',
                'views': [(view_id_form.id, 'form')],
                'target': 'new',
                'view_mode': 'form',
                'context': ctx,
            }

    def _prepare_history_point_value(self, store: str, point_type='new', reason='', points_used=0, points_back=0):
        self.ensure_one()
        pos = self
        return {
            'partner_id': pos.partner_id.id,
            'store': store,
            'pos_order_id': pos.id,
            'date_order': pos.date_order,
            'points_fl_order': pos.point_order + pos.point_event_order + sum([x.point_addition for x in pos.lines]) + sum(
                [x.point_addition_event for x in pos.lines]),
            'point_order_type': point_type,
            'reason': reason or pos.name or '',
            'points_used': abs(sum([line.point / 1000 for line in pos.lines])),  # go back to edit
            'points_back': 0,  # go back to edit
            'points_store': pos.point_order + pos.point_event_order + sum([x.point_addition for x in pos.lines]) + sum(
                [x.point_addition_event for x in pos.lines]) - abs(sum([line.point / 1000 for line in pos.lines])) - 0
        }

    def _get_store_brand_from_program(self):
        self.ensure_one()
        if self.program_store_point_id.brand_id.id == self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id:
            return 'format'
        elif self.program_store_point_id.brand_id.id == self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id:
            return 'forlife'
        else:
            return None

    @api.depends('program_store_point_id')
    def _compute_point_order(self):
        valid_money_payment_method = 0  # X
        valid_money_product = 0  # Y
        for rec in self:
            if not rec.partner_id:
                rec.point_order = 0
                rec.point_event_order = 0
            else:
                branch_id = rec.program_store_point_id.brand_id.id
                brand_format = self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id
                brand_tokyolife = self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id
                if branch_id == brand_format:
                    is_purchased = self.partner_id.is_purchased_of_format or False
                elif branch_id == brand_tokyolife:
                    is_purchased = self.partner_id.is_purchased_of_forlife or False
                else:
                    is_purchased = False
                valid_method_ids = rec.program_store_point_id.payment_method_ids.ids
                valid_product_ids = rec.program_store_point_id.points_product_ids.filtered(
                    lambda x: x.state == 'effective' and x.from_date < rec.date_order < x.to_date).product_ids.ids
                for pay in rec.payment_ids:
                    if pay.payment_method_id.id in valid_method_ids:
                        valid_money_payment_method += pay.amount
                event_valid = self.get_event_match(pos_order=rec)
                if not rec.is_refund_order and not rec.is_change_order:
                    for pro in rec.lines:
                        if pro.product_id.id in valid_product_ids:
                            valid_money_product += pro.price_subtotal_incl

                    money_value = valid_money_payment_method - valid_money_product  # Z
                    if money_value < 0:
                        money_value = 0
                    # is_purchased_of_format, is_purchased_of_forlife = rec.partner_id._check_is_purchased()
                    rec.point_order = rec.get_point_order(money_value, branch_id, is_purchased)
                    if event_valid:
                        domain = [('id', 'in', [x.partner_id.id for x in self.env['contact.event.follow'].sudo().search([('event_id', '=', event_valid.id)])])]
                        partner_condition = self.env['res.partner'].search(domain)
                        if rec.partner_id.id in partner_condition.ids or not partner_condition:
                            rec.point_event_order = int(money_value / event_valid.value_conversion) * event_valid.point_addition  # b
                        else:
                            rec.point_event_order = 0
                    else:
                        rec.point_event_order = 0
                else:
                    # rec.point_order = 999
                    total_price_refund_product = sum(rec.lines.filtered(lambda x: x.product_id.is_product_auto is False and x.price_subtotal_incl < 0).mapped('price_subtotal_incl'))  # X1
                    total_price_product_auto = sum(rec.lines.filtered(lambda x: x.product_id.is_product_auto is True).mapped('price_subtotal_incl'))  # X2
                    total_product_change = sum(rec.lines.filtered(lambda x: x.product_id.is_product_auto is False and x.price_subtotal_incl > 0 and x.product_id.id in valid_product_ids).mapped('price_subtotal_incl'))  # Y
                    money_value = valid_money_payment_method - total_price_refund_product - total_price_product_auto - total_product_change
                    rec.point_order = rec.get_point_order(money_value, branch_id, is_purchased)
                    if event_valid:
                        domain = [('id', 'in', [x.partner_id.id for x in self.env['contact.event.follow'].sudo().search([('event_id', '=', event_valid.id)])])]
                        partner_condition = self.env['res.partner'].search(domain)
                        if rec.partner_id.id in partner_condition.ids or not partner_condition:
                            rec.point_event_order = int(money_value / event_valid.value_conversion) * event_valid.point_addition  # b
                        else:
                            rec.point_event_order = 0
                    else:
                        rec.point_event_order = 0
    # Tách hàm này để cộng thêm điểm tích lũy theo hạng thẻ khách hàng
    def get_point_order(self, money_value, brand_id, is_purchased):
        if self.program_store_point_id.value_conversion <= 0:
            return 0
        if is_purchased:
            return int(money_value / self.program_store_point_id.value_conversion) * self.program_store_point_id.point_addition
        else:
            return int(money_value / self.program_store_point_id.value_conversion) * self.program_store_point_id.point_addition * self.program_store_point_id.first_order

    def get_event_match(self, pos_order):
        point_events = pos_order.program_store_point_id.event_ids.filtered(lambda x: x.from_date <= pos_order.date_order <= x.to_date and x.state == 'effective' and (
                    not x.store_ids or pos_order.config_id.store_id.id in x.store_ids.ids))
        time = pos_order.date_order
        time = time.strftime("%Y-%m-%d %H:%M:%S")
        create_Date = self._format_time_zone(time)
        month_of_order = create_Date.month
        day_of_order = create_Date.day
        day_of_week_order = create_Date.weekday()
        hour_of_order = create_Date.hour
        if point_events:
            for event_valid in point_events:
                months_of_event = event_valid.month_ids
                days_of_event = event_valid.dayofmonth_ids
                day_of_weeks_event = event_valid.dayofweek_ids
                hours_of_event = event_valid.hour_ids
                if all([months_of_event, days_of_event, day_of_weeks_event, hours_of_event]):
                    if month_of_order in [x.code for x in months_of_event] and day_of_order in [x.code for x in days_of_event] and \
                            day_of_week_order in [x.code for x in day_of_weeks_event] and hour_of_order in [x.code for x in hours_of_event]:
                        return event_valid
                else:
                    if not months_of_event and not days_of_event and not day_of_weeks_event and not hours_of_event:
                        return event_valid
                    if not all([months_of_event, days_of_event, day_of_weeks_event, hours_of_event]):
                        if month_of_order in [x.code for x in months_of_event]:
                            return event_valid
                        if day_of_order in [x.code for x in days_of_event]:
                            return event_valid
                        if day_of_week_order in [x.code for x in day_of_weeks_event]:
                            return event_valid
                        if hour_of_order in [x.code for x in hours_of_event]:
                            return event_valid
        return False

    @api.model
    def _order_fields(self, ui_order):
        data = super(PosOrder, self)._order_fields(ui_order)
        if (data['partner_id'] and 'allow_for_point' in ui_order and ui_order.get('allow_for_point') is True) or ('is_refund_product' in ui_order and ui_order.get('is_refund_product')) or ('is_change_product' in ui_order and ui_order['is_change_product']):
            program_promotion = self.get_program_promotion(data)
            if program_promotion:
                data['program_store_point_id'] = program_promotion.id
                data['allow_for_point'] = ui_order.get('allow_for_point', False)
        return data

    @api.model
    def get_program_promotion(self, data):
        if self._context.get('from_PointsConsumptionPos'):
            create_Date = data['date_order'].replace('T', ' ')[:19]
        else:
            create_Date = data['date_order']
        session = self.env['pos.session'].sudo().search([('id', '=', data['session_id'])], limit=1)
        store = session.config_id.store_id
        # query = "select id from points_promotion where id in (select points_promotion_id from points_promotion_store_rel where store_id = {}) " \
        #         "and state = 'in_progress' and from_date < '{}' and to_date > '{}' " \
        #         "and brand_id ={} " \
        #         "limit 1".format(store.id, create_Date, create_Date, store.brand_id.id)
        # self._cr.execute(query)
        # program_promotion = self.env.cr.fetchall()
        program_promotion = self.env['points.promotion'].sudo().search(
            ['|', ('store_ids', 'in', store.id), ('store_ids', '=', False), ('state', '=', 'in_progress'), ('from_date', '<=', create_Date),
             ('to_date', '>=', create_Date),
             ('brand_id', '=', store.brand_id.id)], limit=1)
        print(program_promotion)
        if self._context.get('from_PointsConsumptionPos'):
            dict_point_consumption_ids = []
            for r in program_promotion.point_consumption_ids:
                dict_point_consumption_ids.append({
                    'id': r.id,
                    'name': r.name,
                    'price': r.lst_price
                })
            return {
                'approve_consumption_point': program_promotion.approve_consumption_point,
                'apply_all': program_promotion.apply_all,
                'point_consumption_ids': dict_point_consumption_ids
            }
        return program_promotion

    def _format_time_zone(self, time):
        datetime_object = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
        utcmoment_naive = datetime_object
        utcmoment = utcmoment_naive.replace(tzinfo=pytz.utc)
        # localFormat = "%Y-%m-%d %H:%M:%S"
        tz = 'Asia/Ho_Chi_Minh'
        create_Date = utcmoment.astimezone(pytz.timezone(tz))
        return create_Date

    def action_point_addition(self):
        if self.point_addition_move_ids.filtered(lambda m: m.state == 'posted'):
            raise UserError(_('Order had already point addition journal entry posted!'))
        move_vals = {
            'ref': self.name,
            'pos_order_id': self.id,
            'move_type': 'entry',
            'date': self.date_order,
            'journal_id': self.program_store_point_id.account_journal_id.id,
            'company_id': self.company_id.id,
            'line_ids': [
                # debit line
                (0, 0, {
                    'account_id': self.program_store_point_id.acc_accumulate_points_id.id,
                    'partner_id': self.program_store_point_id.point_customer_id.id,
                    'debit': (self.point_order + self.point_event_order + sum([x.point_addition for x in self.lines]) + sum(
                        [x.point_addition_event for x in self.lines])) * 1000,
                    'credit': 0.0,
                }),
                # credit line
                (0, 0, {
                    'account_id': self.program_store_point_id.point_customer_id.property_account_receivable_id.id,
                    'partner_id': self.program_store_point_id.point_customer_id.id,
                    'debit': 0.0,
                    'credit': (self.point_order + self.point_event_order + sum([x.point_addition for x in self.lines]) + sum(
                        [x.point_addition_event for x in self.lines])) * 1000,
                }),
            ]

        }
        move = self.env['account.move'].create(move_vals)._post()
        self.point_addition_move_ids |= move
        return True

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result.update({
            'total_order_line_point_used': order.total_order_line_point_used,
            'total_order_line_redisual': order.total_order_line_redisual,
            'allow_for_point': order.allow_for_point
        })
        return result
