# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Số PR', 'Ngày PR', 'Số PO', 'Ngày PO', 'NCC', 'Mã hàng', 'Tên hàng', 'SL', 'Đơn giá',
    'CK (%)', 'Thành tiền', 'SL nhập kho', 'SL chưa nhập kho', 'SL lên hóa đơn'
]


class ReportNum13(models.TransientModel):
    _name = 'report.num13'
    _inherit = 'report.base'
    _description = 'Report on the status of PO'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    po_number = fields.Char(string='PO number')

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
