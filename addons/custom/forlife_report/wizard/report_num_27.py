# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Số yêu cầu', 'Ngày yêu cầu', 'Ngày kế hoạch', 'Ghi chú',
    'Kho', 'Số phiếu kho', 'STT dòng', 'Barcode (*)', 'Tên SP',
    'Màu', 'Size', 'Số lượng yêu cầu', 'Đơn vị tính (*)', 'Số lượng xác nhận',
    'Lý do', 'Trung tâm chi phí', 'Mã vụ việc', 'Lệnh sản xuất', 'Mã tài sản'
]


class ReportNum27(models.TransientModel):
    _name = 'report.num27'
    _inherit = 'report.base'
    _description = 'Báo cáo danh sách phiếu nhập_xuất khác'

    request_id = fields.Many2many('forlife.other.in.out.request', string='Số yêu cầu', domain=[('status', 'not in', ('cancel', 'reject'))])
    location_id = fields.Many2one('stock.location', string='Kho')
    type = fields.Selection([('import', 'Nhập khác'), ('export', 'Xuất khác')], string='Loại nhập/xuất', required=True)
    status = fields.Selection([('approved', 'Chưa hoàn thành'), ('done', 'Đã hoàn thành')], string='Trạng thái')

    def _get_query(self):
        self.ensure_one()
        attr_value = self.env['res.utility'].get_attribute_code_config()
        query = f"""
            select
                t1.name as ten
                , TO_CHAR(
                    t1.create_date,
                    'dd/mm/yyyy'
                ) as ngay_yc
                , TO_CHAR(
                    t4.date,
                    'dd/mm/yyyy'
                ) as ngay_kh
                , '' as ghi_chu
                , t3.complete_name as kho
                , t2.name as so_phieu
                , ROW_NUMBER () OVER (PARTITION BY t4.picking_id ORDER BY t4.id) num
                , t5.barcode as barcode
                , COALESCE(t6.name->>'vi_VN', t6.name->>'en_US') AS ten_sp
                , attr.attrs->>'{attr_value.get('mau_sac', '')}' AS mau
                , attr.attrs->>'{attr_value.get('size', '')}' AS size
                , t4.product_uom_qty as sl_yc
                , COALESCE(t7.name->>'vi_VN', t7.name->>'en_US') as dvt
                , '' as sl_xn
                , t11.name as ly_do
                , COALESCE(t10.name->>'vi_VN', t10.name->>'en_US') as tt_cp
                , t8.name as ma_vv
                , t9.name as lsx
                , '' as ma_ts
                
                
            from
                forlife_other_in_out_request t1
            join stock_picking t2 on
                t1.id = t2.other_import_export_request_id
            join stock_location t3 on
                t2.location_id = t3.id
            join stock_move t4 on
                t2.id = t4.picking_id
            join product_product t5 on t4.product_id = t5.id
            join product_template t6 on t5.product_tmpl_id = t6.id
            left join (
                SELECT
                    product_id,
                    json_object_agg(attrs_code, value) AS attrs
                FROM (
                    SELECT
                        pp.id AS product_id,
                        pa.attrs_code AS attrs_code,
                        array_agg(COALESCE(pav.name::json -> 'vi_VN', pav.name::json -> 'en_US')) AS value
                    FROM
                        product_template_attribute_line ptal
                    LEFT JOIN product_product pp ON pp.product_tmpl_id = ptal.product_tmpl_id
                    LEFT JOIN product_attribute_value_product_template_attribute_line_rel rel ON rel.product_template_attribute_line_id = ptal.id
                    LEFT JOIN product_attribute pa ON ptal.attribute_id = pa.id
                    LEFT JOIN product_attribute_value pav ON pav.id = rel.product_attribute_value_id
                    WHERE
                        pa.attrs_code IS NOT NULL
                    GROUP BY
                        pp.id,
                        pa.attrs_code
                ) AS att
                GROUP BY product_id
            ) attr ON attr.product_id = t5.id
            left join uom_uom t7 on t4.product_uom = t7.id
            left join occasion_code t8 on t4.occasion_code_id = t8.id
            left join forlife_production t9 on t4.work_production = t9.id
            left join account_analytic_account t10 on t4.account_analytic_id = t10.id
            left join stock_location t11 on t4.reason_id = t11.id
            
            where 1 = 1
            
        """

        if self.request_id:
            query += f""" and t1.id = any(array{self.request_id.ids})"""
        if self.location_id and (self.type and self.type == 'import'):
            query += f""" and t2.location_dest_id = {self.location_id.id}"""
        if self.location_id and (self.type and self.type == 'export'):
            query += f""" and t2.location_id = {self.location_id.id}"""
        if self.status:
            query += f""" and t1.status = '{self.status}'"""
        if self.type and self.type == 'import':
            query += f""" and t2.other_import is true"""
        if self.type and self.type == 'export':
            query += f""" and t2.other_export is true"""
        query += " ORDER BY t2.name, num;"
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
        sheet = workbook.add_worksheet('Báo cáo danh sách phiếu nhập/xuất khác')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo danh sách phiếu nhập/xuất khác', formats.get('header_format'))
        sheet.write(2, 0, 'Số yêu cầu: %s' % self.request_id.mapped('name') or '', formats.get('italic_format'))
        sheet.write(2, 2, 'Kho: %s' % (self.location_id.name or ''),formats.get('italic_format'))
        sheet.write(2, 4, 'Trạng thái: %s' % (dict(self._fields['status'].selection).get(self.status)),formats.get('italic_format'))
        sheet.write(2, 6, 'Loại nhập/xuất: %s' % (dict(self._fields['type'].selection).get(self.type)),formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('ten'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ngay_yc'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ngay_kh'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ghi_chu'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('kho'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('so_phieu'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('num'), formats.get('int_number_format'))
            sheet.write(row, 7, value.get('barcode'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('ten_sp'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('mau'), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('size'), formats.get('int_number_format'))
            sheet.write(row, 11, value.get('sl_yc'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('dvt'), formats.get('int_number_format'))
            sheet.write(row, 13, value.get('sl_xn'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('ly_do'), formats.get('int_number_format'))
            sheet.write(row, 15, value.get('tt_cp'), formats.get('int_number_format'))
            sheet.write(row, 16, value.get('ma_vv'), formats.get('int_number_format'))
            sheet.write(row, 17, value.get('lsx'), formats.get('int_number_format'))
            sheet.write(row, 18, value.get('ma_ts'), formats.get('int_number_format'))
            row += 1
