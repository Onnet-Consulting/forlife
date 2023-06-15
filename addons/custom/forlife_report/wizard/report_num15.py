# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Chi nhánh', 'Bộ phận', 'Ngày', 'Số HĐ', 'Tên KH', 'Voucher', 'Tên chương trình', 'Bắt đầu', 'Kết thúc'
]


class ReportNum15(models.TransientModel):
    _name = 'report.num15'
    _inherit = 'report.base'
    _description = 'Search Voucher Used'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    voucher = fields.Char(string='Voucher', required=True)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        sql = f"""
select
    row_number() over ()                                                as num,
    (select name from store where id in (
        select store_id from pos_config where id in (
            select config_id from pos_session where id = po.session_id
            ) 
        ) limit 1
    )                                                                   as store_name,
    hd.name                                                             as department,
    to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY')    as date,
    po.pos_reference                                                    as invoice_num,
    rp.name                                                             as customer_name,
    vv.name                                                             as voucher,
    pv.name                                                             as program_name,
    to_char(vv.start_date + '{tz_offset} h'::interval, 'DD/MM/YYYY')    as start_date,
    to_char(vv.end_date + '{tz_offset} h'::interval, 'DD/MM/YYYY')      as end_date
from pos_voucher_line pvl
    join voucher_voucher vv on vv.id = pvl.voucher_id
    join program_voucher pv on pv.id = vv.program_voucher_id
    join hr_department hd on hd.id = pv.derpartment_id
    join pos_order po on po.id = pvl.pos_order_id
    left join res_partner rp on rp.id = po.partner_id
where po.brand_id = {self.brand_id.id} and vv.name ilike '%{self.voucher}%'
  and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
order by num
"""
        return sql

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Tra cứu mã Voucher đã sử dụng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Tra cứu mã Voucher đã sử dụng', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 4, 'Voucher: %s' % (self.voucher or ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('store_name'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('department'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('date'), formats.get('center_format'))
            sheet.write(row, 4, value.get('invoice_num'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('customer_name'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('voucher'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('program_name'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('start_date'), formats.get('center_format'))
            sheet.write(row, 9, value.get('end_date'), formats.get('center_format'))
            row += 1
