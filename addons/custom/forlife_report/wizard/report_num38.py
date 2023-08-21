# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError
import copy

TITLES = [
    'STT',
    'Tên kho',
    'Tên nội bộ',
    'Mã kho',
    'Mã nội bộ',
    'Nhóm kho',
    'Loại kho',
    'Tên địa điểm',
    'Mã địa điểm',
    'Loại địa điểm',
    'Kiểu địa điểm',
    'Địa điểm kí gửi',
    'Địa chỉ kho',
    'Công ty',
    'Thương hiệu',
    'Diện tích kho',
    'Số điện thoại',
    'Quản lý kho',
    'Trạng thái',
    'Khu vực kinh doanh',
    'Khu vực địa lý',
    'Khu vực thời tiết',
]


class ReportNum38(models.TransientModel):
    _name = 'report.num38'
    _inherit = ['report.base']
    _description = 'Báo cáo danh sách kho hàng_địa điểm'

    company_ids = fields.Many2many('res.company', string='Công ty', required=True)
    wh_group_ids = fields.Many2many('warehouse.group', string='Nhóm kho')
    wh_ids = fields.Many2many('stock.warehouse', string='Kho', domain="[('warehouse_gr_id', 'in', wh_group_ids)]")
    show_location = fields.Boolean(string='Chi tiết địa điểm', default=False)

    def _get_query(self, allowed_company):
        self.ensure_one()
        tz_offset = self.tz_offset

        query = f"""
            select 
                sw.name as ten,
                sw.name_internal as ten_nb,
                sw.code as ma_kho,
                sw.warehouse_code_internal as ma_nb,
                wg.name as nhom_kho,
                swt.name as loai_kho,
                {'''
                sl.complete_name as dia_diem,
                sl.code as ma_dia_diem,
                slt.name as loai_dia_diem,
                case when sl.usage = 'supplier' then 'Địa điểm nhà cung cấp'
                    when sl.usage = 'view' then 'Xem' 
                    when sl.usage = 'internal' then 'Địa điểm nội bộ' 
                    when sl.usage = 'customer' then 'Địa điểm khách hàng' 
                    when sl.usage = 'inventory' then 'Thất thoát/kiểm kê'
                    when sl.usage = 'production' then 'Địa điểm sản xuất'
                    when sl.usage = 'import/export' then 'Nhập khác/Xuất khác'
                    else '' end as kieu_dia_diem,
                sl.id_deposit as ky_gui,
                ''' if self.show_location else ''
                }
                CONCAT_WS(', ',
                sw.street,
                sw.street2,
                sw.city,
                rcs.name,
                coalesce (rc.name->>'vi_VN',
                rc.name->>'en_US')) as dia_chi,
                rcom.name as congty,
                rb.name as thuong_hieu,
                sw.square as dien_tich,
                sw.phone as dien_thoai,
                he.name as quan_ly,
                sws.name as trang_thai,
                rsp.name as kv_kinhdoanh,
                rlp.name as kv_dialy,
                wpi.name as kv_thoitiet
                
            from
                stock_warehouse sw
            left join warehouse_group wg on
                sw.warehouse_gr_id = wg.id
            left join stock_warehouse_type swt on
                sw.whs_type = swt.id
            left join res_country_state rcs on
                sw.state_id = rcs.id
            left join res_country rc on
                sw.country_id = rc.id
            left join res_company rcom on
                sw.company_id = rcom.id
            left join res_brand rb on
                sw.brand_id = rb.id
            left join hr_employee he on
                sw.manager_id = he.id
            left join stock_warehouse_status sws on
                sw.status_ids = sws.id
            left join res_sale_province rsp on
                sw.sale_province_id = rsp.id
            left join res_location_province rlp on
                sw.loc_province_id = rlp.id
            left join res_weather_province wpi on
                sw.weather_province_id = wpi.id
            {'''
                left join stock_location sl on sw.id = sl.warehouse_id
                left join stock_location_type slt on sl.stock_location_type_id = slt.id
            ''' if self.show_location else ''}
            where 1= 1
        """
        if self.wh_ids:
            query += f""" and sw.id = any(array{self.wh_ids.ids})"""
        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query(allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        titles = copy.copy(TITLES)
        if not self.show_location:
            titles.remove('Tên địa điểm')
            titles.remove('Mã địa điểm')
            titles.remove('Loại địa điểm')
            titles.remove('Kiểu địa điểm')
            titles.remove('Địa điểm kí gửi')
        values.update({
            'titles': titles,
            "data": data,
            "column_add": self.show_location
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo danh sách kho hàng_địa điểm')
        sheet.set_row(0, 25)
        sheet.set_row(4, 30)
        sheet.write(0, 0, 'Báo cáo danh sách kho hàng/địa điểm', formats.get('header_format'))
        sheet.write(2, 0, 'Kho: %s' % self.wh_ids.mapped('name'), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(data.get('titles')) - 1, 20)
        row = 5
        index = 1
        col_index = 7 if not self.show_location else 12
        for value in data['data']:
            sheet.write(row, 0, index, formats.get('center_format'))
            sheet.write(row, 1, value.get('ten'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ten_nb'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ma_kho'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ma_nb'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('nhom_kho'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('loai_kho'), formats.get('normal_format'))
            if self.show_location:
                sheet.write(row, 7, value.get('dia_diem') or '', formats.get('normal_format'))
                sheet.write(row, 8, value.get('ma_dia_diem') or '', formats.get('normal_format'))
                sheet.write(row, 9, value.get('loai_dia_diem') or '', formats.get('normal_format'))
                sheet.write(row, 10, value.get('kieu_dia_diem') or '', formats.get('normal_format'))
                sheet.write(row, 11, value.get('ky_gui') or '', formats.get('normal_format'))

            sheet.write(row, col_index, value.get('dia_chi'), formats.get('normal_format'))
            sheet.write(row, col_index + 1, value.get('congty'), formats.get('normal_format'))
            sheet.write(row, col_index + 2, value.get('thuong_hieu'), formats.get('normal_format'))
            sheet.write(row, col_index + 3, value.get('dien_tich'), formats.get('normal_format'))
            sheet.write(row, col_index + 4, value.get('dien_thoai'), formats.get('normal_format'))
            sheet.write(row, col_index + 5, value.get('quan_ly'), formats.get('normal_format'))
            sheet.write(row, col_index + 6, value.get('trang_thai'), formats.get('normal_format'))
            sheet.write(row, col_index + 7, value.get('kv_kinhdoanh'), formats.get('normal_format'))
            sheet.write(row, col_index + 8, value.get('kv_dialy'), formats.get('normal_format'))
            sheet.write(row, col_index + 9, value.get('kv_thoitiet'), formats.get('normal_format'))
            row += 1
            index += 1
