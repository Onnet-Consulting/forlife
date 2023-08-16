# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Nhà cung cấp (*)',
    'Loại mua hàng (*)',
    'Tiền tệ (*)',
    'Tỷ giá (*)',
    'Ngày đặt hàng (*)',
    'Chính sách thanh toán',
    'Ngày nhận (*)',
    'Hạn xử lý (*)',
    'Kho nhận',
    'Hợp đồng khung?',
    'Có hóa đơn hay không?',
    'Ghi chú',
    'Chi tiết/Sản phẩm (*)',
    'Chi tiết/Hàng tặng',
    'Chi tiết/Số lượng đặt mua (*)',
    'Chi tiết/Đơn vị mua (*)',
    'Chi tiết/Số lượng quy đổi (*)',
    'Chi tiết/Giá nhà cung cấp (*)',
    'Chi tiết/Địa điểm kho (*)',
    'Chi tiết/Thuế(%)',
    'Chi tiết/Chiết khấu(%)',
    'Chi tiết/Lệnh sản xuất',
    'Chi tiết/Ngày nhận (*)',
    'Chi tiết/Phiếu yêu cầu',
    'Chi tiết/STT line phiếu yêu cầu',
    'Thuế nhập khẩu/Mã sản phẩm',
    'Thuế nhập khẩu/Tổng tiền',
    'Thuế nhập khẩu/% Thuế nhập khẩu',
    'Thuế nhập khẩu/Tổng tiền thuế nhập khẩu',
    'Thuế nhập khẩu/% Thuế tiêu thụ đặc biệt',
    'Thuế nhập khẩu/Tổng tiền thuế tiêu thụ đặc biệt',
    'Thuế nhập khẩu/% Thuế GTGT',
    'Thuế nhập khẩu/Tổng tiền thuế GTGT',
    'Chi phí/Mã sản phẩm',
    'Chi phí/Loại tiền',
    'Chi phí/Tỷ giá',
    'Chi phí/Tiền ngoại tệ',
    'Chi phí/Tiền nội tệ',
    'Chi phí/Trước thuế?',
]


class ReportNum31(models.TransientModel):
    _name = 'report.num31'
    _inherit = 'report.base'
    _description = 'Báo cáo template import PO'

    company_id = fields.Many2one('res.company', string='Công ty')
    date_from = fields.Date(string='Từ ngày', required=1)
    date_to = fields.Date(string='Đến ngày', required=1)
    purchase_rq_id = fields.Many2many('purchase.request', 'rp3_pr', string='Số PR')
    status = fields.Selection([('open', 'Mở'), ('close', 'Đóng'), ('all', 'Tất cả')], string='Trạng thái')
    request_id = fields.Many2one('res.users', string='Người yêu cầu')
    receive_id = fields.Many2one('hr.employee', string='Người nhận')
    brand_id = fields.Many2one('product.category', string='Thương hiệu', domain=[('parent_id', '=', False)])
    group_id = fields.Many2one('product.category', string='Nhóm hàng', domain="[('parent_id', '=', brand_id), ('parent_id', '!=', False)]")
    line_id = fields.Many2one('product.category', string='Dòng hàng', domain="[('parent_id', '=', group_id), ('parent_id', '!=', False)]")
    structure_id = fields.Many2one('product.category', string='Kết cấu', domain="[('parent_id', '=', line_id), ('parent_id', '!=', False)]")

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        query = f"""
            select 
                rp.name as nha_cc,
                '' as loai_mua_hang,
                '' as tien_te,
                '' as ti_gia,
                '' as ngay_dat_hang,
                '' as chinh_sach_tt,
                '' as ngay_nhan,
                '' as han_xu_ly,
                '' as kho_nhan,
                '' as hop_dong_khung,
                '' as co_hoa_don_khong,
                '' as ghi_chu,
                pp.barcode  as barcode,
                '' as hang_tang,
                (prl.purchase_quantity - prl.order_quantity) as sl_dat_mua,
                coalesce (uu.name->>'vi_VN', uu.name->>'en_US') as dv_dat_mua,
                prl.exchange_quantity as sl_quy_doi,
                '' as gia_ncc,
                '' as dia_diem_kho,
                '' as thue,
                '' as chiet_khau,
                '' as lenh_sx,
                '' as ngay_nhan,
                pr.name as so_phieu_yc,
                row_number () over (partition by prl.request_id  order by prl.id) num,
                '' as ma_sp,
                '' as tong_tien,
                '' as thue_nk,
                '' as tong_tien_thue_nk,
                '' as thue_db,
                '' as tong_tien_thue_db,
                '' as thue_vat,
                '' as tong_tien_thue_vat,
                '' as cp_ma_sp,
                '' as cp_loai_tien,
                '' as cp_ti_gia,
                '' as cp_tien_ngoai_te,
                '' as cp_tien_noi_te,
                '' as cp_tien_truoc_thue
            from
                purchase_request pr
            join purchase_request_line prl on
                pr.id = prl.request_id
            left join product_product pp on
                prl.product_id = pp.id
            left join product_template pt on
                pp.product_tmpl_id = pt.id
            left join (
                select
                    pc.id,
                    pc.name as pc1,
                    pc1.id as id_pc2,
                    pc1.name as pc2,
                    pc2.id as id_pc3,
                    pc2.name as pc3,
                    pc3.id as id_pc4,
                    pc3.name as pc4,
                    pc4.id as id_pc5,
                    pc4.name as pc5
                from
                    product_category pc
                join product_category pc1 on
                    pc.parent_id = pc1.id
                join product_category pc2 on
                    pc1.parent_id = pc2.id
                join product_category pc3 on
                    pc2.parent_id = pc3.id
                join product_category pc4 on
                    pc3.parent_id = pc4.id
            ) as p_cate on
                p_cate.id = pt.categ_id
                
            left join res_partner rp on prl.vendor_code = rp.id
            left join uom_uom uu on prl.purchase_uom = uu.id 
            where 1 = 1 and {format_date_query('pr.request_date', tz_offset)} between '{self.date_from}' and '{self.date_to}'

        """

        if self.company_id:
            query += f""" and pr.company_id = {self.company_id.id}"""
        if self.purchase_rq_id:
            query += f""" and pr.id = any(array{self.purchase_rq_id.ids})"""
        if self.status and self.status == 'open':
            query += f""" and (prl.is_close is false or prl.is_close is null)"""
        if self.status and self.status == 'close':
            query += f""" and (prl.is_close is true or prl.is_close is not null)"""
        if self.status and self.status == 'all':
            query += f""" and (prl.is_all_line is true or prl.is_all_line is not null)"""
        if self.request_id:
            query += f""" and pr.user_id = {self.request_id.id}"""
        if self.receive_id:
            query += f""" and pr.receiver_id = {self.receive_id.id}"""
        if self.brand_id:
            query += f""" and p_cate.id_pc5 = {self.brand_id.id}"""
        if self.group_id:
            query += f""" and p_cate.id_pc4 = {self.group_id.id}"""
        if self.line_id:
            query += f""" and p_cate.id_pc3 = {self.line_id.id}"""
        if self.structure_id:
            query += f""" and p_cate.id_pc2 = {self.structure_id.id}"""

        query += " ORDER BY pr.id;"
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
        sheet = workbook.add_worksheet('Báo cáo template import PO')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo danh sách CCDC và TSCD', formats.get('header_format'))
        sheet.write(2, 0, 'Công ty: %s' % self.company_id.name or '', formats.get('italic_format'))
        sheet.write(2, 2, 'Số PR: %s' % (self.purchase_rq_id.mapped('name') or ''), formats.get('italic_format'))
        sheet.write(2, 4, 'Trạng thái: %s' % (self.status or ''), formats.get('italic_format'))
        sheet.write(2, 6, 'Từ ngày: %s' % (self.date_from.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 8, 'Đến ngày: %s' % (self.date_to.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(3, 2, 'Người yêu cầu: %s' % (self.request_id.name or ''), formats.get('italic_format'))
        sheet.write(3, 4, 'Người nhận: %s' % (self.receive_id.name or ''), formats.get('italic_format'))
        sheet.write(3, 6, 'Thương hiệu: %s' % (self.brand_id.name or ''), formats.get('italic_format'))
        sheet.write(3, 8, 'Nhóm hàng: %s' % (self.group_id.name or ''), formats.get('italic_format'))
        sheet.write(3, 10, 'Dòng hàng: %s' % (self.line_id.name or ''), formats.get('italic_format'))
        sheet.write(3, 12, 'Kết cấu: %s' % (self.structure_id.name or ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('nha_cc'), formats.get('normal_format'))
            sheet.write(row, 1, value.get('loai_mua_hang'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('tien_te'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ti_gia'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ngay_dat_hang'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('chinh_sach_tt'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ngay_nhan'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('han_xu_ly'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('kho_nhan'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('hop_dong_khung'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('co_hoa_don_khong'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('ghi_chu'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('barcode'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('hang_tang'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('sl_dat_mua'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('dv_dat_mua'), formats.get('normal_format'))
            sheet.write(row, 16, value.get('sl_quy_doi'), formats.get('normal_format'))
            sheet.write(row, 17, value.get('gia_ncc'), formats.get('normal_format'))
            sheet.write(row, 18, value.get('dia_diem_kho'), formats.get('normal_format'))
            sheet.write(row, 19, value.get('thue'), formats.get('normal_format'))
            sheet.write(row, 20, value.get('chiet_khau'), formats.get('normal_format'))
            sheet.write(row, 21, value.get('lenh_sx'), formats.get('normal_format'))
            sheet.write(row, 22, value.get('ngay_nhan'), formats.get('normal_format'))
            sheet.write(row, 23, value.get('so_phieu_yc'), formats.get('normal_format'))
            sheet.write(row, 24, value.get('num'), formats.get('normal_format'))
            sheet.write(row, 25, value.get('ma_sp'), formats.get('normal_format'))
            sheet.write(row, 26, value.get('tong_tien'), formats.get('normal_format'))
            sheet.write(row, 27, value.get('thue_nk'), formats.get('normal_format'))
            sheet.write(row, 28, value.get('tong_tien_thue_nk'), formats.get('normal_format'))
            sheet.write(row, 29, value.get('thue_db'), formats.get('normal_format'))
            sheet.write(row, 30, value.get('tong_tien_thue_db'), formats.get('normal_format'))
            sheet.write(row, 31, value.get('thue_vat'), formats.get('normal_format'))
            sheet.write(row, 32, value.get('tong_tien_thue_vat'), formats.get('normal_format'))
            sheet.write(row, 33, value.get('cp_ma_sp'), formats.get('normal_format'))
            sheet.write(row, 34, value.get('cp_loai_tien'), formats.get('normal_format'))
            sheet.write(row, 35, value.get('cp_ti_gia'), formats.get('normal_format'))
            sheet.write(row, 36, value.get('cp_tien_ngoai_te'), formats.get('normal_format'))
            sheet.write(row, 37, value.get('cp_tien_noi_te'), formats.get('normal_format'))
            sheet.write(row, 38, value.get('cp_tien_truoc_thue'), formats.get('normal_format'))
            row += 1