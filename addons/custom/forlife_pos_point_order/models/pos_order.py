from odoo import api, fields, models
from datetime import datetime
import pytz


class PosOrder(models.Model):
    _inherit = 'pos.order'

    point_order = fields.Integer('Point Order', compute='_compute_point_order', store=True)
    point_event_order = fields.Integer('Point event Order', compute='_compute_point_order', store=True)
    total_point = fields.Integer('Total Point', readonly=True)
    program_store_point_id = fields.Many2one('points.promotion', 'Program Store Point')

    @api.model
    def _process_order(self, order, draft, existing_order):
        pos_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        HistoryPoint = self.env['partner.history.point']
        if not existing_order:
            pos = self.env['pos.order'].browse(pos_id)
            if pos.partner_id.is_member_app_format or pos.partner_id.is_member_app_forlife:
                if pos.program_store_point_id:
                    if pos.program_store_point_id.brand_id.id == self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id:
                        store = 'format'
                    elif pos.program_store_point_id.brand_id.id == self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id:
                        store = 'forlife'
                    else:
                        return super(PosOrder, self)._process_order(order, draft, existing_order)
                    if store is not None:
                        HistoryPoint.sudo().create({
                            'partner_id': pos.partner_id.id,
                            'store': store,
                            'date_order': pos.date_order,
                            'points_fl_order': pos.point_order + pos.point_event_order + sum([x.point_addition for x in pos.lines]) + sum(
                                [x.point_addition_event for x in pos.lines]),
                            'point_order_type': 'new',
                            'reason': pos.name,
                            'points_used': 5,  # go back to edit
                            'points_back': 5,  # go back to edit
                            'points_store': pos.point_order + pos.point_event_order + sum([x.point_addition for x in pos.lines]) + sum(
                                [x.point_addition_event for x in pos.lines]) - 5 - 5

                        })
                        pos.partner_id._compute_reset_day(pos.date_order, pos.program_store_point_id.point_expiration, store)
                        pos.action_point_addition()
        return pos_id

    @api.depends('program_store_point_id')
    def _compute_point_order(self):
        valid_money_payment_method = 0  # X
        valid_money_product = 0  # Y
        for rec in self:
            valid_method_ids = rec.program_store_point_id.payment_method_ids.ids
            valid_product_ids = rec.program_store_point_id.points_product_ids.product_ids.ids
            for pay in rec.payment_ids:
                if pay.payment_method_id.id in valid_method_ids:
                    valid_money_payment_method += pay.amount

            for pro in rec.lines:
                if pro.id in valid_product_ids:
                    valid_money_product += pro.price_subtotal_incl

            money_value = valid_money_payment_method - valid_money_product  # Z
            if rec.partner_id.is_purchased:
                rec.point_order = int(
                    money_value / rec.program_store_point_id.value_conversion * rec.program_store_point_id.point_addition) if rec.program_store_point_id.value_conversion > 0 else 0  # a
            else:
                rec.point_order = int(
                    money_value / rec.program_store_point_id.value_conversion * rec.program_store_point_id.point_addition) * rec.program_store_point_id.first_order if rec.program_store_point_id.value_conversion > 0 else 0  # a
            event_valid = self.get_event_match(pos_order=rec)
            if event_valid:
                rec.point_event_order = int(money_value / event_valid.value_conversion * event_valid.point_addition)  # b
            else:
                rec.point_event_order = 0

    def get_event_match(self, pos_order):
        point_events = pos_order.program_store_point_id.event_ids.filtered(lambda x: x.from_date <= pos_order.date_order <= x.to_date)
        if point_events:
            event_valid = point_events[0]
            time = pos_order.date_order
            time = time.strftime("%Y-%m-%d %H:%M:%S")
            create_Date = self._format_time_zone(time)
            month_of_order = create_Date.month
            day_of_order = create_Date.day
            day_of_week_order = create_Date.weekday()
            hour_of_order = create_Date.hour
            months_of_event = event_valid.month_ids
            days_of_event = event_valid.dayofmonth_ids
            day_of_weeks_event = event_valid.dayofweek_ids
            hours_of_event = event_valid.hour_ids
            if month_of_order in [x.code for x in months_of_event] and day_of_order in [x.code for x in days_of_event] and \
                    day_of_week_order in [x.code for x in day_of_weeks_event] and hour_of_order in [x.code for x in hours_of_event]:
                return event_valid
            else:
                return False
        return False

    @api.model
    def _order_fields(self, ui_order):
        data = super(PosOrder, self)._order_fields(ui_order)
        program_promotion = self._get_program_promotion(data)
        if program_promotion:
            data['program_store_point_id'] = program_promotion.id
        return data

    def _get_program_promotion(self, data):
        create_Date = self._format_time_zone(data['date_order'])
        session = self.env['pos.session'].sudo().search([('id', '=', data['session_id'])], limit=1)
        store = session.config_id.store_id
        program_promotion = self.env['points.promotion'].sudo().search(
            [('store_ids', 'in', store.id), ('state', '=', 'in_progress'), ('from_date', '<=', create_Date), ('to_date', '>=', create_Date),
             ('brand_id', '=', store.brand_id.id)], limit=1)
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
        move_vals = {
            'ref': self.name,
            'move_type': 'entry',
            'date': self.date_order,
            'journal_id': self.program_store_point_id.account_journal_id.id,
            'company_id': self.company_id.id,
            'line_ids': [
                # debit line
                (0, 0, {
                    'account_id': self.program_store_point_id.acc_accumulate_points_id.id,
                    'partner_id': self.program_store_point_id.point_customer_id.id,
                    'debit': self.point_order + self.point_event_order + sum([x.point_addition for x in self.lines]) + sum(
                        [x.point_addition_event for x in self.lines])*1000,
                    'credit': 0.0,
                }),
                # credit line
                (0, 0, {
                    'account_id': self.program_store_point_id.point_customer_id.property_account_receivable_id.id,
                    'partner_id': self.program_store_point_id.point_customer_id.id,
                    'debit': 0.0,
                    'credit': self.point_order + self.point_event_order + sum([x.point_addition for x in self.lines]) + sum(
                        [x.point_addition_event for x in self.lines])*1000,
                }),
            ]

        }
        self.env['account.move'].create(move_vals)
        return True
