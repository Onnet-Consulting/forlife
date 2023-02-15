# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import pytz
import copy
from datetime import timedelta

REPORT_HEADER = ['STT', 'Chi nhánh', 'Mã chi nhánh', 'Khu vực', 'Mã KH', 'Tên KH', 'Mã HĐ', 'Ngày mua hàng', 'Ngày đánh giá', 'Đánh giá', 'Bình luận', 'Trạng thái']
POP_INDEX_IN_FORM_REPORT = (3, 2)  # xóa cột khu vực và mã chi nhánh trên phom báo cáo


class NetPromoterScoreReport(models.TransientModel):
    _name = 'net.promoter.score.report'
    _description = 'Net Promoter Score Report'

    def _default_header(self):
        result = self.get_view_header()
        return result[0] + result[1]

    name = fields.Char('Name', default='Báo cáo NPS')
    from_date = fields.Datetime('Date', required=True)
    to_date = fields.Datetime('To Date', required=True)
    customer_code = fields.Text('Customer Code')
    invoice_number = fields.Text('Invoice Number')
    min_point = fields.Integer('Level', default=0)
    max_point = fields.Integer('Max Point', default=100)
    view_report = fields.Html('View Report', default=_default_header)
    brand_ids = fields.Many2many('res.brand', string='Brands', required=True)

    def get_view_header(self):
        header = copy.copy(REPORT_HEADER)
        for index in POP_INDEX_IN_FORM_REPORT:
            header.pop(index)
        return [f'<table class="table table-bordered"><tr style="text-align: center; background: #031d74c7; color: #ffffff;"><th>{"</th><th>".join(header)}</th></tr>', '</table>']

    def btn_search(self):
        result = self.filter_data()
        data = ''
        for line in result[1:]:
            style = ' style="background: #0a0a0a3d;"' if int(line[0]) % 2 == 0 else ''
            data += f'<tr{style}><td style="text-align: center;">{"</td><td>".join(line)}</td></tr>'
        header = self.get_view_header()
        self.view_report = header[0] + data + header[1]

    def filter_data(self):
        domain = ['&', '&', ('status', '=', '1'), ('point', '>=', self.min_point), ('point', '<=', self.max_point)]
        if self.from_date:
            domain.insert(0, '&')
            domain += [('invoice_date', '>=', self.from_date)]
        if self.to_date:
            domain.insert(0, '&')
            domain += [('invoice_date', '<', self.to_date + timedelta(days=1))]
        if self.brand_ids:
            domain.insert(0, '&')
            domain += [('brand', 'in', self.brand_ids.mapped('code'))]
        if self.customer_code:
            cus_code_domain = [('customer_code', 'like', i.strip()) for i in self.customer_code.split(',')]
            domain.insert(0, '&')
            domain += ['|'] * (len(cus_code_domain) - 1)
            domain += cus_code_domain
        if self.invoice_number:
            inv_num_domain = [('invoice_number', 'like', i.strip()) for i in self.invoice_number.split(',')]
            domain.insert(0, '&')
            domain += ['|'] * (len(inv_num_domain) - 1)
            domain += inv_num_domain
        result = self.env['forlife.comment'].search(domain)
        data = [REPORT_HEADER]
        row = 1
        for line in result:
            val = [str(row), line.store_name, line.store_code, line.areas, line.customer_code, line.customer_name, line.invoice_number,
                   line.invoice_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y'),
                   line.comment_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y') if line.comment_date else '',
                   str(line.point), line.comment or '', str(line.status)]
            if self._context.get('pop_colum', False):
                for index in POP_INDEX_IN_FORM_REPORT:
                    val.pop(index)
            data.append(val)
            row += 1
        return data
