# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get

from pytz import timezone
from datetime import datetime


def format_date_query(column_name, tz_offset):
    """
    Because DB save datetime value in UTC timezone, so
    when we compare a 'datetime' value with a 'date' value,
    we must convert datetime value to date value by adding a 'tz_offset'
    @param column_name: str - original column name
    @param tz_offset: int - timezone offset (seconds)
    @return : str - formatted column name with date conversion
    """
    return f"""to_date(to_char({column_name} + interval '{tz_offset} hours', 'YYYY-MM-DD'), 'YYYY-MM-DD')"""


class ReportBase(models.AbstractModel):
    _name = 'report.base'
    _description = 'Report Base'

    tz = fields.Selection(_tz_get, default="Asia/Ho_Chi_Minh", string="Timezone",
                          help='Timezone used for selecting datetime data from DB', required=True)
    tz_offset = fields.Integer(compute='_compute_timezone_offset', string="Timezone offset",
                               help='Timezone offset in hours')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    def print_xlsx(self):
        ...

    def view_report(self):
        ...

    @api.depends('tz')
    def _compute_timezone_offset(self):
        for rec in self:
            localize_now = datetime.now(timezone(self.tz))
            rec.tz_offset = int(localize_now.utcoffset().total_seconds() / 3600)
