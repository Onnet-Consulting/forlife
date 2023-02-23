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
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    def print_xlsx(self):
        report = self.env.ref('forlife_report.%s_xlsx' % self._name.replace('.', '_'))
        return {
            'type': 'ir.actions.act_url',
            'name': report.name,
            'url': '/report/xlsx/%s/%d' % (report.report_name, self.id),
            'target': 'self'
        }

    def view_report(self):
        ...

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
