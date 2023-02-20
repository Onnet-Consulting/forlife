# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import pytz
import copy
from datetime import timedelta

REPORT_HEADER = ['STT', 'Chi nhánh', 'Mã chi nhánh', 'Khu vực', 'Mã KH', 'Tên KH', 'Mã HĐ', 'Ngày mua hàng', 'Ngày đánh giá', 'Đánh giá', 'Bình luận', 'Trạng thái']
POP_INDEX_IN_FORM_REPORT = (3, 2)  # xóa cột khu vực và mã chi nhánh trên phom báo cáo
DATA_NOT_FOUND = f'<tr style="text-align: center; color: #000000;"><td colspan="{len(REPORT_HEADER) - len(POP_INDEX_IN_FORM_REPORT)}"><h3>Không tìm thấy bản ghi nào !</h3></td></tr>'
MIN_RECORD_PER_PAGE = 80
MAX_RECORD_PER_PAGE = 200


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
    record_per_page = fields.Integer(default=200)
    number_of_page = fields.Integer(default=1)
    current_page = fields.Integer(default=0)
    number_of_record = fields.Char()
    record_by_page = fields.Json()

    @api.onchange('record_per_page', 'from_date', 'to_date', 'min_point', 'max_point', 'brand_ids', 'customer_code', 'invoice_number')
    def onchange_record_per_page(self):
        if self.from_date and self.to_date and self.brand_ids:
            values = self.with_context(pop_colum=True, onchange=True).btn_search()
        else:
            header = self.get_view_header()
            values = {
                'view_report': header[0] + DATA_NOT_FOUND + header[1],
                'number_of_page': 1,
                'current_page': 0,
                'number_of_record': False,
                'record_by_page': False,
                'record_per_page': min(max(self.record_per_page, MIN_RECORD_PER_PAGE), MAX_RECORD_PER_PAGE),
            }
        self.view_report = values.get('view_report')
        self.record_per_page = values.get('record_per_page', self.record_per_page)
        self.number_of_page = values.get('number_of_page')
        self.current_page = values.get('current_page')
        self.number_of_record = values.get('number_of_record')
        self.record_by_page = values.get('record_by_page')

    def get_view_header(self):
        header = copy.copy(REPORT_HEADER)
        for index in POP_INDEX_IN_FORM_REPORT:
            header.pop(index)
        return [f'<table class="table table-bordered"><tr style="text-align: center; background: #017e84; color: #ffffff;"><th>{"</th><th>".join(header)}</th></tr>', '</table>']

    def btn_search(self):
        values = dict(self._check_record_per_page())
        result, values = self.filter_data([], values)
        return self.generate_data(result, values)

    def btn_reset_searching(self):
        header = self.get_view_header()
        self.sudo().write({
            'customer_code': False,
            'invoice_number': False,
            'min_point': 0,
            'max_point': 100,
            'brand_ids': False,
            'view_report': header[0] + header[1],
            'number_of_page': 1,
            'current_page': 0,
            'number_of_record': False,
            'record_by_page': False,
            'record_per_page': min(max(self.record_per_page, MIN_RECORD_PER_PAGE), MAX_RECORD_PER_PAGE),
        })

    def btn_next_page(self):
        self.load_new_page(1)

    def btn_previous_page(self):
        self.load_new_page(-1)

    def load_new_page(self, types):
        values = {}
        page = ((self.current_page or self.number_of_page) + types) % self.number_of_page
        page_data = self.record_by_page.get(str(page), ['', []])
        record_per_page = self.record_by_page.get('record_per_page')
        if self.record_per_page != record_per_page:
            values.update({'record_per_page': record_per_page})
        values.update({'number_of_record': page_data[0], 'current_page': page})
        result, values = self.filter_data([('id', 'in', page_data[1])], values)
        self.generate_data(result, values)

    def filter_data(self, domain, values):
        if not self._context.get('paging', False):
            domain = ['&', '&', '&', ('status', '=', '1'), ('point', '>=', self.min_point), ('point', '<=', self.max_point), ('brand', 'in', self.brand_ids.mapped('code'))]
            if self.from_date:
                domain.insert(0, '&')
                domain += [('invoice_date', '>=', self.from_date)]
            if self.to_date:
                domain.insert(0, '&')
                domain += [('invoice_date', '<', self.to_date + timedelta(days=1))]
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
        records = self.env['forlife.comment'].search(domain)
        if self._context.get('pop_colum', False) and not self._context.get('paging', False):
            records, values = self._check_paging(records, values)
        return self.prepare_report_data(records), values

    def _check_paging(self, records, values):
        values = dict(values)
        total_records = len(records)
        record_per_page = values.get('record_per_page', self.record_per_page)
        values.update({'current_page': 0})
        if total_records > record_per_page:
            _return = records[:record_per_page]
            number_of_page = 0
            record_by_page = {'record_per_page': record_per_page}
            while records:
                record_in_page = records[:min(len(records), record_per_page)].ids
                records = records[min(len(records), record_per_page):]
                record_by_page.update({
                    number_of_page: [
                        f'{number_of_page * record_per_page + 1}-{number_of_page * record_per_page + len(record_in_page)} / {total_records}',
                        record_in_page,
                    ]
                })
                number_of_page += 1
            values.update({
                'number_of_page': number_of_page or 1,
                'record_by_page': record_by_page,
                'number_of_record': f'1-{record_per_page} / {total_records}'
            })
            return _return, values
        values.update({
            'number_of_page': 1,
            'record_by_page': False,
            'number_of_record': '1-{0} / {0}'.format(total_records) if total_records else ''
        })
        return records, values

    def prepare_report_data(self, records):
        data = [REPORT_HEADER] if not self._context.get('pop_colum', False) else []
        row = 1
        for line in records:
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

    def generate_data(self, result, values):
        values = dict(values)
        data = ''
        for line in result:
            style = ' style="background: #0a0a0a3d;"' if int(line[0]) % 2 == 0 else ''
            data += f'<tr{style}><td style="text-align: center;">{"</td><td>".join(line)}</td></tr>'
        header = self.get_view_header()
        values.update({
            'view_report': header[0] + (data or DATA_NOT_FOUND) + header[1],
        })
        if not self._context.get('onchange'):
            self.sudo().write(values)
        return values

    def _check_record_per_page(self):
        values = {}
        record_per_page = min(max(self.record_per_page, MIN_RECORD_PER_PAGE), MAX_RECORD_PER_PAGE)
        if self.record_per_page != record_per_page:
            values.update({'record_per_page': record_per_page})
        return values
