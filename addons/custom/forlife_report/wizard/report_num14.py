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
    _description = 'Search Code Used'

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
        tz_offset = self.tz_offset
        sql = f"""
select
    row_number() over ()    as num,
    ppg.name                as program_name,
    pc.name                 as code,
    po.pos_reference        as invoice_num,
    ''                      as invoice_num_online,
    rp.name                 as customer_name,
    pp.default_code         as product_code,
    pol.full_product_name   as product_name,
    pol.qty                 as qty
from promotion_usage_line pul
    join promotion_code pc on pc.id = pul.code_id
    join promotion_program ppg on ppg.id = pul.program_id
    join pos_order_line pol on pol.id = pul.order_line_id
    join pos_order po on po.id = pol.order_id
    join product_product pp on pp.id = pol.product_id
    left join res_partner rp on rp.id = po.partner_id
where po.brand_id = {self.brand_id.id} and pc.name ilike '%{self.code}%'
  and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
order by num
"""
        return sql

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
        sheet = workbook.add_worksheet('Tra cứu mã Code đã sử dụng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Tra cứu mã Code đã sử dụng', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 4, 'Mã code: %s' % (self.code or ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('program_name'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('code'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('invoice_num'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('invoice_num_online'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('customer_name'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('product_code'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('qty', 0), formats.get('float_number_format'))
            row += 1
