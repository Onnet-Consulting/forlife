from odoo import api, fields, models
from datetime import datetime
import pytz


class PosOrder(models.Model):
    _inherit = 'pos.order'

    point_order = fields.Integer('Point Order', readonly=True)
    point_event_order = fields.Integer('Point event Order', readonly=True)
    total_point = fields.Integer('Total Point', readonly=True)
    program_store_point_id = fields.Many2one('points.promotion', 'Program Store Point')

    @api.model
    def _process_order(self, order, draft, existing_order):
        pos_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        pos_order = self.env['pos.order'].browse(pos_id)
        # point_events = pos_order.program_store_point_id.event_ids.filtered(lambda x: x.from_date <= pos_order.date_order <= x.to_date)
        # print(point_events)
        # print(point_event[0])
        return pos_id

    def _compute_point_order(self, pos_order):
        valid_money_payment_method = 0  # X
        valid_money_product = 0  # Y
        valid_method_ids = pos_order.program_store_point_id.payment_method_ids.ids
        valid_product_ids = pos_order.program_store_point_id.points_product_ids.product_ids.ids

        for pay in pos_order.payment_ids:
            if pay.payment_method_id.id in valid_method_ids:
                valid_money_payment_method += pay.amount

        for pro in pos_order.lines:
            if pro.id in valid_product_ids:
                valid_money_product += pro.price_subtotal_incl
        money_value = valid_money_payment_method - valid_money_product  # Z
        point_order = money_value/(pos_order.program_store_point_id.value_conversion * pos_order.program_store_point_id.point_addition)
        point_event_order = money_value/(pos_order.program_store_point_id.value_conversion * pos_order.program_store_point_id.point_addition)

    def get_event_match(self, pos_order):
        point_events = pos_order.program_store_point_id.event_ids.filtered(lambda x: x.from_date <= pos_order.date_order <= x.to_date)
        event_valid = point_events[0]
        month_of_order = pos_order.date_order.month
        day_of_order = pos_order.date_order.day
        day_of_week_order = pos_order.date_order.month
        hour_of_order = pos_order.date_order.hour

    @api.model
    def _order_fields(self, ui_order):
        data = super(PosOrder, self)._order_fields(ui_order)
        # print(create_Date)
        # print(self.session_id.config_id.store_id)
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
             ('x_brand_id', '=', store.x_brand_id.id)], limit=1)
        return program_promotion

    def _format_time_zone(self, time):
        datetime_object = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
        utcmoment_naive = datetime_object
        utcmoment = utcmoment_naive.replace(tzinfo=pytz.utc)
        # localFormat = "%Y-%m-%d %H:%M:%S"
        tz = 'Asia/Ho_Chi_Minh'
        create_Date = utcmoment.astimezone(pytz.timezone(tz))
        return create_Date
