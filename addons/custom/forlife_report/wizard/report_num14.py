# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Tên chương trình', 'Mã code', 'Số HĐ', 'Số HĐ online', 'Tên KH', 'Mã hàng', 'Tên hàng', 'SL'
]


class ReportNum14(models.TransientModel):
    _name = 'report.num14'
    _inherit = 'report.base'
    _description = 'Search Code - Voucher Used'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    code = fields.Char(string='Code', required=True)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        sql = f"""
"""
        return sql

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        query = self._get_query()
        # self._cr.execute(query)
        # data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": {},
        })
        return values
