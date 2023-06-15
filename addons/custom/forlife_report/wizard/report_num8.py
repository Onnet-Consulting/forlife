# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Mã CN', 'Tên CN', 'Mã Voucher', 'Loại Voucher', 'Đối tượng', 'Đầu mã Voucher', 'Bộ phận',
    'Tên chương trình', 'Mục đích sử dụng', 'Hóa đơn sử dụng', 'Ngày sử dụng', 'Giá trị sử dụng'
]


class ReportNum8(models.TransientModel):
    _name = 'report.num8'
    _inherit = 'report.base'
    _description = 'Report voucher detail'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    order_id = fields.Many2one('pos.order', string='Invoice Num')
    voucher = fields.Char(string='Voucher code')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.order_id = False

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        po_conditions = f'and po.id = {self.order_id.id}' if self.order_id else ''
        voucher_conditions = f"and vv.name ilike '%{self.voucher}%'" if self.voucher else ''
        query = f"""
select row_number() over ()                                                 as num,
    (select array[coalesce(code, ''), coalesce(name, '')]
     from store where id in (
        select store_id from pos_config where id in (
            select config_id from pos_session where id in (
                select session_id from pos_order where id = po.id 
            )
        )
    ))                                                                      as store_info,
    vv.name 																as voucher_code,
    case when pv.apply_many_times is true then 'Voucher sử dụng nhiều lần'
        else 'Voucher sử dụng 1 lần' end									as voucher_type,
    sv.applicable_object 												 	as object,
    substr(vv.name, 0, 7) 													as voucher_code8,
    hd.name 																as department,
    pv.name 																as program_name,
    pv.details         														as purpose,
    po.pos_reference 														as order_name,
    to_char(po.date_order + interval '7 hours', 'DD/MM/YYYY')				as date,
    pv_line.price_used														as value
from pos_order po
    join pos_voucher_line pv_line on po.id = pv_line.pos_order_id
    join voucher_voucher vv on vv.id = pv_line.voucher_id
    left join program_voucher pv on pv.id = vv.program_voucher_id
    left join setup_voucher sv on sv.id = pv.purpose_id
    left join hr_department hd on hd.id = pv.derpartment_id
where po.brand_id = {self.brand_id.id} 
and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
{po_conditions}
{voucher_conditions}
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
        sheet = workbook.add_worksheet('Báo cáo chi tiết hóa đơn áp dụng voucher')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo chi tiết hóa đơn áp dụng voucher', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(3, 0, 'Số hóa đơn: %s' % (self.order_id.name or ''), formats.get('italic_format'))
        sheet.write(3, 2, 'Mã voucher: %s' % (self.voucher or ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(5, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 6
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('store_info', [''])[0], formats.get('normal_format'))
            sheet.write(row, 2, value.get('store_info', ['', ''])[1], formats.get('normal_format'))
            sheet.write(row, 3, value.get('voucher_code'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('voucher_type'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('object'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('voucher_code8'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('department'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('program_name'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('purpose'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('order_name'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('date'), formats.get('center_format'))
            sheet.write(row, 12, value.get('value'), formats.get('int_number_format'))
            row += 1
