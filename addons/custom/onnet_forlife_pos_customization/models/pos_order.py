from odoo import api, fields, models
from datetime import datetime
import pytz


class PosOrder(models.Model):
    _inherit = 'pos.order'

    point_order = fields.Integer('Point (+) Order', readonly=True)
    point_event_order = fields.Integer('Point event Order', readonly=True)
    total_point = fields.Integer('Total Point', readonly=True)
    program_store_point = fields.Many2one('points.promotion', 'Program Store Point')

    @api.model
    def _order_fields(self, ui_order):
        data = super(PosOrder, self)._order_fields(ui_order)
        # print(create_Date)
        # print(self.session_id.config_id.store_id)
        program_promotion = self._get_program_promotion(data)
        print(program_promotion)
        return data

    def _get_program_promotion(self, data):
        create_Date = self._format_time_zone(data['date_order'])
        session = self.env['pos.session'].sudo().search([('id', '=', data['session_id'])], limit=1)
        store = session.config_id.store_id
        program_promotion = self.env['points.promotion'].sudo().search(
            [('store_ids', 'in', store.id), ('state', '=', 'in_progress'), ('from_date', '<=', create_Date), ('to_date','>=',create_Date),('brand_id','=',store.brand_id)])
        return program_promotion

    def _format_time_zone(self, time):
        datetime_object = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
        utcmoment_naive = datetime_object
        utcmoment = utcmoment_naive.replace(tzinfo=pytz.utc)
        # localFormat = "%Y-%m-%d %H:%M:%S"
        tz = 'Asia/Ho_Chi_Minh'
        create_Date = utcmoment.astimezone(pytz.timezone(tz))
        return create_Date
