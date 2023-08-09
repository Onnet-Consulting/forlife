# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Số yêu cầu', 'Ngày yêu cầu', 'Hạn xử lý', 'Ghi chú',
    'Từ kho', 'Đến kho', 'Số phiếu điều chuyển', 'STT dòng', 'Barcode (*)', 'Tên SP',
    'Màu', 'Size', 'SL kế hoạch', 'Đơn vị tính (*)', 'Số lượng xuất (*)',
    'Số lượng nhập (*)', 'Từ LSX', 'Đến LSX', 'Loại phiếu'
]


class ReportNum26(models.TransientModel):
    _name = 'report.num26'
    _inherit = 'report.base'
    _description = 'Báo cáo danh sách phiếu điều chuyển'

    request_id = fields.Many2many('stock.transfer.request', string='Số yêu cầu', domain=[('state', 'not in', ('reject', 'cancel'))])
    location_id = fields.Many2one('stock.location', string='Từ kho')
    location_dest_id = fields.Many2one('stock.location', string='Đến kho')
    status = fields.Selection([('approved', 'Chưa xuất'), ('out_approve', 'Xác nhận xuất')], string='Trạng thái')

    def _get_query(self):
        self.ensure_one()
        attr_value = self.env['res.utility'].get_attribute_code_config()
        query = f"""
            SELECT
                str.name AS ten,
                TO_CHAR(
                    str.request_date,
                    'dd/mm/yyyy'
                ) AS ngay_yeu_cau,
                TO_CHAR(
                    str.date_planned,
                    'dd/mm/yyyy'
                ) AS han_xu_ly,
                st.note AS ghi_chu,
                sl1.complete_name AS tu_kho,
                sl2.complete_name AS den_kho,
                st.name AS so_phieu_dc,
                ROW_NUMBER() OVER (PARTITION BY stl.stock_transfer_id ORDER BY stl.id) num,
                pp.barcode AS barcode,
                COALESCE(pt.name->>'vi_VN', pt.name->>'en_US') AS ten_sp,
                attr.attrs->>'{attr_value.get('mau_sac', '')}' AS mau,
                attr.attrs->>'{attr_value.get('size', '')}' AS size,
                stl.qty_plan AS sl_ke_hoach,
                COALESCE(uu.name->>'vi_VN', uu.name->>'en_US') AS dvt,
                stl.qty_out AS sl_xuat,
                stl.qty_in AS sl_nhap,
                fp1.name AS lsx_tu,
                fp2.name AS lsx_den,
                st.type as loai_phieu
            FROM
                stock_transfer_request str
            LEFT JOIN stock_transfer st ON st.stock_request_id = str.id
            JOIN stock_location sl1 ON st.location_id = sl1.id
            JOIN stock_location sl2 ON st.location_dest_id = sl2.id
            JOIN stock_transfer_line stl ON st.id = stl.stock_transfer_id
            LEFT JOIN forlife_production fp1 ON stl.work_from = fp1.id
            LEFT JOIN forlife_production fp2 ON stl.work_to = fp2.id
            LEFT JOIN uom_uom uu ON stl.uom_id = uu.id
            JOIN product_product pp ON stl.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN (
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
            ) attr ON attr.product_id = pp.id
            WHERE
                1 = 1
        """
        if self.request_id:
            query += f""" and str.id = any(array{self.request_id.ids})"""
        if self.location_id:
            query += f""" and sl1.id = {self.location_id.id}"""
        if self.location_dest_id:
            query += f""" and sl2.id = {self.location_dest_id.id}"""
        if self.status:
            query += f""" and st.state = '{self.status}'"""
        query += " ORDER BY str.name, num;"
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
        sheet = workbook.add_worksheet('Báo cáo danh sách phiếu điều chuyển')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo danh sách phiếu điều chuyển', formats.get('header_format'))
        sheet.write(2, 0, 'Số yêu cầu: %s' % self.request_id.mapped('name') or '', formats.get('italic_format'))
        sheet.write(2, 2, 'Từ kho: %s đến kho: %s' % (
            self.location_id.name or '',
            self.location_dest_id.name or ''),
            formats.get('italic_format'))
        sheet.write(2, 4, 'Trạng thái: %s' % (dict(self._fields['status'].selection).get(self.status)),
                    formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('ten'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ngay_yeu_cau'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('han_xu_ly'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ghi_chu'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('tu_kho'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('den_kho'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('so_phieu_dc'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('num'), formats.get('int_number_format'))
            sheet.write(row, 8, value.get('barcode'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('ten_sp'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('mau'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('size'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('sl_ke_hoach'), formats.get('int_number_format'))
            sheet.write(row, 13, value.get('dvt'), formats.get('int_number_format'))
            sheet.write(row, 14, value.get('sl_xuat'), formats.get('int_number_format'))
            sheet.write(row, 15, value.get('sl_nhap'), formats.get('int_number_format'))
            sheet.write(row, 16, value.get('lsx_tu'), formats.get('normal_format'))
            sheet.write(row, 17, value.get('lsx_den'), formats.get('normal_format'))
            sheet.write(row, 18, dict(self.env['stock.transfer']._fields['type'].selection).get(value.get('loai_phieu')), formats.get('normal_format'))
            row += 1
