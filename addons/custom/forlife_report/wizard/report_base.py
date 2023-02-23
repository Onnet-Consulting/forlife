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
        return {
            'type': 'ir.actions.act_url',
            'name': self._description,
            'url': '/custom/download/xlsx/%s/%s/%d' % (self._description, self._name, self.id),
            'target': 'self'
        }

    def view_report(self):
        ...

    @api.depends('tz')
    def _compute_timezone_offset(self):
        for rec in self:
            localize_now = datetime.now(timezone(self.tz))
            rec.tz_offset = int(localize_now.utcoffset().total_seconds() / 3600)

    def get_format_workbook(self, workbook):
        header_format = {
            'bold': 1,
            'size': 20
        }
        title_format = {
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#dbeef4'
        }
        normal_format = {
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        }
        datetime_format = {
            'num_format': "dd/mm/yy hh:mm:ss",
        }
        datetime_format.update(normal_format)
        float_number_format = {}
        int_number_format = {}

        float_number_format.update(normal_format)
        int_number_format.update(normal_format)
        float_number_title_format = float_number_format.copy()
        float_number_title_format.update(title_format)
        int_number_title_format = int_number_format.copy()
        int_number_title_format.update(title_format)

        title_format = workbook.add_format(title_format)
        datetime_format = workbook.add_format(datetime_format)
        normal_format = workbook.add_format(normal_format)
        header_format = workbook.add_format(header_format)

        float_number_format = workbook.add_format(float_number_format)
        float_number_format.set_num_format('#,##0.00')
        int_number_format = workbook.add_format(int_number_format)
        int_number_format.set_num_format('#,##0')

        float_number_title_format = workbook.add_format(float_number_title_format)
        float_number_title_format.set_num_format('#,##0.00')
        int_number_title_format = workbook.add_format(int_number_title_format)
        int_number_title_format.set_num_format('#,##0')

        return {
            'header_format': header_format,
            'title_format': title_format,
            'datetime_format': datetime_format,
            'normal_format': normal_format,
            'float_number_format': float_number_format,
            'int_number_format': int_number_format,
            'float_number_title_format': float_number_title_format,
            'int_number_title_format': int_number_title_format,
        }
