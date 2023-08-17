# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Phân loại', 'Mã tài sản/CCDC', 'Tên tài sản/CCDC', 'Mã CCDC lưu kho', 'Tên CCDC lưu kho',
    'Trạng thái', 'Đơn vị tính', 'Số lượng', 'Nhân viên', 'Bộ phận',
    'Vị trí',
]


class ReportNum28(models.TransientModel):
    _name = 'report.num29'
    _inherit = 'report.base'
    _description = 'Báo cáo danh sách CCDC và TSCD'

    company_id = fields.Many2one('res.company', string='Công ty')
    department_id = fields.Many2one('account.analytic.account', string='Bộ phận', domain="[('company_id', '=', company_id)]")
    location_id = fields.Many2one('asset.location', string='Vị trí')
    date_from = fields.Date(string='Từ ngày', required=1)
    date_to = fields.Date(string='Đến ngày', required=1)

    def _get_query(self):
        self.ensure_one()
        attr_value = self.env['res.utility'].get_attribute_code_config()
        tz_offset = self.tz_offset
        query = f"""
            select 
                aa.type as phan_loai,
                aa.code as ma,
                aa.name as ten,
                aa.item_code as ma_luu_kho,
                pt.name as ten_luu_kho,
                (case when aa.state = 'using' then 'Đang sử dụng' else 'Đã thanh lý' end) as trang_thai,
                aa.unit as dvt,
                aa.quantity as sl,
                concat_ws('-', he.code, he.name) as nhan_vien,
                concat_ws('-', aaa.code, coalesce (aaa.name->>'vi_VN', aaa.name->>'en_US')) as bo_phan,
                al.name as vi_tri
            from assets_assets aa
            left join product_product pp on pp.barcode = aa.item_code 
            left join product_template pt on pp.product_tmpl_id = pt.id
            left join hr_employee he on aa.employee = he.id 
            left join account_analytic_account aaa on aa.dept_code = aaa.id
            left join asset_location al on aa.location = al.id 
            
            where aa.type in ('TSCD', 'CCDC') and {format_date_query('aa.doc_date', tz_offset)} between '{self.date_from}' and '{self.date_to}'
        """

        if self.company_id:
            query += f""" and aa.company_id = {self.company_id.id}"""
        if self.location_id:
            query += f""" and al.id = {self.location_id.id}"""
        if self.department_id:
            query += f""" and aaa.id = '{self.department_id.id}'"""
        query += " ORDER BY aa.id;"
        return query

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
        sheet = workbook.add_worksheet('Báo cáo danh sách CCDC và TSCD')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo danh sách CCDC và TSCD', formats.get('header_format'))
        sheet.write(2, 0, 'Công ty: %s' % self.company_id.name or '', formats.get('italic_format'))
        sheet.write(2, 2, 'Bộ phận: %s' % (self.department_id.name or ''), formats.get('italic_format'))
        sheet.write(2, 4, 'Vị trí: %s' % (self.location_id.name or ''), formats.get('italic_format'))
        sheet.write(2, 6, 'Từ ngày: %s' % (self.date_from.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 8, 'Đến ngày: %s' % (self.date_to.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('phan_loai'), formats.get('normal_format'))
            sheet.write(row, 1, value.get('ma'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ten'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ma_luu_kho'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ten_luu_kho'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('trang_thai'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('dvt'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('sl'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('nhan_vien'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('bo_phan'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('vi_tri'), formats.get('normal_format'))
            row += 1