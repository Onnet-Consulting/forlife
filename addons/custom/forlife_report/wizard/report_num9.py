# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Đầu mã Voucher', 'Bộ phận', 'Loại Voucher', 'Đối tượng', 'Tên chương trình',
    'Mục đích sử dụng', 'SL phát hành', 'Mệnh giá', 'Thành tiền', 'Ngày bắt đầu', 'Ngày kết thúc'
]


class ReportNum9(models.TransientModel):
    _name = 'report.num9'
    _inherit = 'report.base'
    _description = 'Report voucher published'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    voucher = fields.Char(string='Voucher code')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        voucher_conditions = f"and vv.name ilike '%{self.voucher}%'" if self.voucher else ''
        query = f"""
with datas as (
    select
        pv.id                                                                   as program_id,
        substr(vv.name, 0, 7) 													as voucher_code8,
        hd.name 																as department,
        case when pv.apply_many_times is true then 'Voucher sử dụng nhiều lần'
            else 'Voucher sử dụng 1 lần' end									as voucher_type,
        sv.applicable_object 												 	as object,
        pv.name 																as program_name,
        pv.details			                									as purpose,
        vv.price          														as value,
        to_char(vv.start_date + interval '7 hours', 'DD/MM/YYYY')				as start_date,
        to_char(vv.end_date + interval '7 hours', 'DD/MM/YYYY')				    as end_date
    from program_voucher pv
        join voucher_voucher vv on pv.id = vv.program_voucher_id
        left join setup_voucher sv on sv.id = pv.purpose_id
        left join hr_department hd on hd.id = pv.derpartment_id
    where pv.brand_id = {self.brand_id.id}
        and {format_date_query("vv.start_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
    {voucher_conditions}
)
select 
    program_id, voucher_code8, department, voucher_type, object, program_name, purpose, value, start_date, end_date,
    count(1) as qty_published,
    row_number() over () as num
from datas
group by program_id, voucher_code8, department, voucher_type, object, program_name, purpose, value, start_date, end_date
order by num
"""
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo voucher phát hành')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo voucher phát hành', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 4, 'Mã voucher: %s' % (self.voucher or ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('voucher_code8'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('department'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('voucher_type'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('object'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('program_name'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('purpose'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('qty_published'), formats.get('int_number_format'))
            sheet.write(row, 8, value.get('value'), formats.get('int_number_format'))
            sheet.write(row, 9, value.get('value', 0) * value.get('qty_published', 0), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('start_date'), formats.get('center_format'))
            sheet.write(row, 11, value.get('end_date'), formats.get('center_format'))
            row += 1
