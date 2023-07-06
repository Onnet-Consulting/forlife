# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Số phiếu yêu cầu', 'Số dòng trên phiếu yêu cầu', 'Mã sản phẩm', 'Tên sản phẩm', 'Số lượng yêu cầu', 'Số lượng thực xuất',
    'Số lượng thực nhận', 'Số lượng còn lại chưa xuất', 'Đơn vị tính', 'Từ kho', 'Đến kho', 'Ngày dự kiến nhận hàng'
]


class ReportNum19(models.TransientModel):
    _name = 'report.num19'
    _inherit = 'report.base'
    _description = 'Stock Transfer Request Report'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    location_ids = fields.Many2many('stock.location', 'report_19_source_loc', string="Whs From", domain="[('usage', '=', 'internal')]")
    location_dest_ids = fields.Many2many('stock.location', 'report_19_dest_loc', string="Whs To", domain="[('usage', '=', 'internal')]")
    str_number = fields.Text('STR number')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        user_lang_code = self.env.user.lang
        sour_loc = (self.env['stock.location'].search([('usage', '=', 'internal')]).ids or [-1]) if not self.location_ids else self.location_ids.ids
        dest_loc = (self.env['stock.location'].search([('usage', '=', 'internal')]).ids or [-1]) if not self.location_dest_ids else self.location_dest_ids.ids
        where_condition = f"""and ({' or '.join("str.name ilike '%s'" % i.strip() for i in self.str_number.split(','))})""" if self.str_number else ''

        sql = f"""
select 
    str.name                                                                           as so_phieu_yc,
    row_number() over (PARTITION BY str.id ORDER BY str.id, trl.id)                    as so_dong_tren_phieu_yc,
    pp.barcode                                                                         as ma_sp,
    coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')          as ten_sp,
    coalesce(trl.plan_quantity, 0)                                                     as sl_yeu_cau,
    (select array[coalesce(sum(qty_out), 0), coalesce(sum(qty_in), 0)]
     from stock_transfer_line where is_parent_done = true and product_str_id = trl.id) as sl_nhap_xuat,
    coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')          as don_vi_tinh,
    s_loc.complete_name                                                                as tu_kho,
    d_loc.complete_name                                                                as den_kho,
    to_char(str.date_planned + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')          as ngay_du_kien
from transfer_request_line trl
    join stock_transfer_request str on str.id = trl.request_id
    join product_product pp on pp.id = trl.product_id
    left join product_template pt on pt.id = pp.product_tmpl_id
    left join uom_uom uom on uom.id = pt.uom_id
    join stock_location s_loc on s_loc.id = trl.location_id
    join stock_location d_loc on d_loc.id = trl.location_dest_id
    where {format_date_query("str.request_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
        and (s_loc.id = any (array{sour_loc}) or d_loc.id = any (array{dest_loc}))
        {where_condition}
order by str.id, trl.id
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
        sheet = workbook.add_worksheet('Báo cáo tình hình thực hiện yêu cầu chuyển kho')
        sheet.set_row(0, 25)
        sheet.set_column(0, len(TITLES) - 1, 18)
        sheet.write(0, 0, 'Báo cáo tình hình thực hiện yêu cầu chuyển kho', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày: %s' % self.from_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 3, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(3, 0, 'Từ kho: %s' % ','.join(self.location_ids.mapped('complete_name')), formats.get('italic_format'))
        sheet.write(3, 3, 'Đến kho: %s' % ','.join(self.location_dest_ids.mapped('complete_name')), formats.get('italic_format'))
        sheet.write(2, 5, 'Số YC: %s' % (self.str_number or ''), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(5, idx, title, formats.get('title_format'))
        row = 6
        for value in data['data']:
            sheet.write(row, 0, value.get('so_phieu_yc'), formats.get('normal_format'))
            sheet.write(row, 1, value.get('so_dong_tren_phieu_yc'), formats.get('int_number_format'))
            sheet.write(row, 2, value.get('ma_sp'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ten_sp'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('sl_yeu_cau'), formats.get('int_number_format'))
            sheet.write(row, 5, value.get('sl_nhap_xuat')[0], formats.get('int_number_format'))
            sheet.write(row, 6, value.get('sl_nhap_xuat')[1], formats.get('normal_format'))
            sheet.write(row, 7, value.get('sl_yeu_cau') - value.get('sl_nhap_xuat')[0], formats.get('int_number_format'))
            sheet.write(row, 8, value.get('don_vi_tinh'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('tu_kho'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('den_kho'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('ngay_du_kien'), formats.get('center_format'))
            row += 1
