# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools.misc import formatLang

from pytz import timezone
from datetime import datetime, timedelta


class ReportBase(models.AbstractModel):
    _name = 'report.base'
    _description = 'Report Base'

    tz = fields.Selection(_tz_get, default="Asia/Ho_Chi_Minh", string="Timezone",
                          help='Timezone used for selecting datetime data from DB', required=True)
    tz_offset = fields.Integer(compute='_compute_timezone_offset', string="Timezone offset",
                               help='Timezone offset in hours')

    @api.depends('tz')
    def _compute_timezone_offset(self):
        for rec in self:
            localize_now = datetime.now(timezone(self.tz))
            rec.tz_offset = int(localize_now.utcoffset().total_seconds() / 3600)

    def convert_datetime_to_utc(self, datetime_value):
        """
        @param datetime_value: date or datetime value in localize timezone
        @return date or datetime in utc
        """
        self.ensure_one()
        if type(datetime_value) is datetime:
            return (datetime_value + timedelta(hours=self.tz_offset)).stftime(DTF)
        # datetime type don't need to convert to utc
        return datetime_value.strftime(DF)

    @api.model
    def format_num(self, num, blank_if_zero=False, digits=0):
        if num is None:
            return ''
        if not num and blank_if_zero:
            return ''
        return formatLang(self.env, num, digits=digits)

    def format_data(self, data, **options):
        number_options = options.get('numbers') or {}
        blank_if_zero = number_options.get('blank_if_zero', False)
        digits = number_options.get('digits', 0)
        data_keys= {}
        if not data:
            return data
        data_keys = list(data[0].keys())