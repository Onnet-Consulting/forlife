# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'ID',
    'Mã barcode',
    'Mã SKU',
    'Mã kĩ thuật',
    'Mã hiển thị',
    'Tên',
    'Tên hàng cũ',
    'Loại sản phẩm',
    'Loại hàng mua',
    'Chính sách tính phí',
    'Chính sách kiểm soát',
    'Thương hiệu',
    'Danh mục sản phẩm',
    'Nhóm hàng',
    'Dòng hàng',
    'Kết cấu',
    'Đối tượng',
    'Nhãn hiệu',
    'Đơn vị tính',
    'Đơn vị mua hàng',
    'Đơn vị tính 2 (quy đổi với npl và bộ đối với hàng hóa)',
    'Hệ số quy đổi',
    'Màu cơ bản',
    'Màu sắc',
    'Ánh màu',
    'Màu phối',
    'Pantone',
    'Màu NCC',
    'Màu cũ',
    'Size',
    'Dải size',
    'Kích thước',
    'Trọng lượng',
    'Khổ vải',
    'Tái sản xuất',
    'Ngày hết hạn',
    'Ngày cảnh báo',
    'Hạn đổi trả',
    'Chất lượng',
    'Năm sản xuất',
    'Mã thiết kế',
    'Mô tả thiết kế',
    'Ngành vải',
    'Chất liệu',
    'Thành phần chất liệu',
    'Subclass 1',
    'Subclass 2',
    'Subclass 3',
    'Subclass 4',
    'Subclass 5',
    'Subclass 6',
    'Subclass 7',
    'Subclass 8',
    'Subclass 9',
    'Subclass 10',
    'Thuộc tính 1',
    'Thuộc tính 2',
    'Mục đích sử dụng',
    'Bộ sưu tập',
    'Nhà thiết kế',
    'Xuất xứ',
    'Mùa vụ',
    'Loại hàng hóa',
    'Hướng dẫn sử dụng',
    'Nguồn hàng',
    'Nhóm sản phẩm đặc trưng',
    'Kênh bán hàng',
    'Vùng bán hàng',
    'Tem nhãn',
    'Ghi chú',
    'Sản phẩm tách mã',
    'Giá bán',
    'Có thể bán được',
    'Có thể mua được',
    'Khả dụng trong POS',
]


class ReportNum37(models.TransientModel):
    _name = 'report.num37'
    _inherit = ['report.base', 'export.excel.client', 'report.category.type']
    _description = 'Báo cáo thông tin sản phẩm'

    product_id = fields.Many2many('product.product', string='Sản phẩm')
    category_code = fields.Char(related='category_type_id.code')
    categ_id = fields.Many2one('product.category', string='Danh mục sản phẩm', domain="[('parent_id', '=', False), ('category_type_id', '=', category_type_id)]")
    brand_id = fields.Many2one('product.category', string='Thương hiệu', domain="[('parent_id', '=', False), ('category_type_id', '=', category_type_id)]")
    group_id = fields.Many2one('product.category', string='Nhóm hàng',
                               domain="[('parent_id', '=', brand_id), ('parent_id', '!=', False)]")
    line_id = fields.Many2one('product.category', string='Dòng hàng',
                              domain="[('parent_id', '=', group_id), ('parent_id', '!=', False)]")
    structure_id = fields.Many2one('product.category', string='Kết cấu',
                                   domain="[('parent_id', '=', line_id), ('parent_id', '!=', False)]")

    @api.onchange('category_type_id')
    def _onchange_category_type_id(self):
        self.update({
            'categ_id': False,
            'brand_id': False,
            'group_id': False,
            'line_id': False,
            'structure_id': False,
        })

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        self.update({
            'group_id': False,
            'line_id': False,
            'structure_id': False,
        })

    def _get_query(self, allowed_company):
        self.ensure_one()
        attr_value = self.env['res.utility'].get_attribute_code_config()

        field_with_brand_id = """
            ct.pc_id as id_thuonghieu,
            ct.pc_name as thuong_hieu,
            ct1.pc_id AS id_nhomhang,
            ct1.pc_name AS nhomhang,
            ct2.pc_id AS id_donghang,
            ct2.pc_name AS donghang,
            ct3.pc_id AS id_ketcau,
            ct3.pc_name AS ketcau,
            ct4.pc_id AS id_danhmuc,
            ct4.pc_name AS dm_sanpham,
        """

        field_with_categ_id = """
            ct.pc_id as id_danhmuc,
            ct.pc_name as dm_sanpham,
            ct1.pc_id AS id_nhomhang,
            ct1.pc_name AS nhomhang,
            ct2.pc_id AS id_donghang,
            ct2.pc_name AS donghang,
            ct3.pc_id AS id_ketcau,
            ct3.pc_name AS ketcau,
            ct4.pc_id AS id_thuonghieu,
            ct4.pc_name AS thuong_hieu,
        """

        query = f"""
            WITH RECURSIVE category_tree AS (
                SELECT
                    pc.id AS pc_id,
                    pc.name AS pc_name,
                    pc.parent_id
                FROM
                    product_category pc
                WHERE
                    pc.parent_id IS NULL
                
                UNION ALL
                
                SELECT
                    pc.id AS pc_id,
                    pc.name AS pc_name,
                    pc.parent_id
                FROM
                    product_category pc
                INNER JOIN category_tree ct ON pc.parent_id = ct.pc_id
                ),
                product_info as (
                select
                pp.id as id,
                pt.categ_id as categ_id,
                pp.barcode as barcode,
                pt.sku_code as sku_code,
                pt.makithuat as makithuat,
                pt.default_code as default_code,
                coalesce (pt.name ->> 'vi_VN',
                pt.name ->> 'en_US') as name,
                pt.tenhangcu as tenhangcu,
                case
                    when pt.detailed_type = 'consu' then 'Tiêu dùng'
                    when pt.detailed_type = 'product' then 'Sản phẩm lưu kho'
                    when pt.detailed_type = 'service' then 'Dịch vụ'
                    when pt.detailed_type = 'asset' then 'Tài sản'
                    when pt.detailed_type = 'event' then 'Vé sự kiện'
                    else ''
                end as loai_sp,
                case
                    when pt.product_type = 'product' then 'Hàng hóa'
                    when pt.product_type = 'service' then 'Dịch vụ'
                    when pt.product_type = 'asset' then 'Tài sản'
                    else ''
                end as loai_mua_hang,
                case
                    when pt.invoice_policy = 'order' then 'Số lượng đặt hàng'
                    when pt.invoice_policy = 'delivery' then 'Số lượng bàn giao'
                    else ''
                end as cs_tinh_phi,
                case
                    when pt.purchase_method = 'purchase' then 'Theo số lượng mua'
                    when pt.purchase_method = 'receive' then 'Theo số lượng nhận'
                    else '' end,
                coalesce (uu.name ->> 'vi_VN',
                uu.name ->> 'en_US') as donvi,
                coalesce (uu2.name ->> 'vi_VN',
                uu2.name ->> 'en_US') as dv_muahang,
                pt.heso as hs_quydoi,
                pt.collection as bosuutap,
                code_design as mathietke,
                '' as mota_thietke,
                pt.special_group_product as nhom_sp_dactrung,
                pt.stamp as tem_nhan,
                pt.note as ghichu,
                pt.pantone as pantone,
                pt.mau_ncc as mau_ncc,
                pt.daisai as daisize,
                pt.trongluong as trongluong,
                pt.khovai as khovai,
                pt.expiration_date as expiration_date,
                pt.warning_date as warning_date,
                pt.number_days_change_refund as number_days_change_refund,
                pt.material_composition as material_composition,
                pt.user_manual as user_manual,
                case when pt.sale_ok is true then 'TRUE' else '' end as cotheban,
                case when pt.purchase_ok is true then 'TRUE' else '' end as cothemua,
                case when pt.pos_ok is true then 'TRUE' else '' end as khadung_pos,
                pt.list_price as price,
                attr.attrs->'{attr_value.get('doi_tuong')}' ->> 0 as doi_tuong,
                attr.attrs->'{attr_value.get('nhan_hieu')}' ->> 0 as nhan_hieu,
                attr.attrs->'{attr_value.get('don_vi_tinh')}' ->> 0 as don_vi_tinh,
                attr.attrs->'{attr_value.get('don_vi_tinh2')}' ->> 0 as don_vi_tinh2,
                attr.attrs->'{attr_value.get('mau_sac')}' ->> 0 as mau_sac,
                attr.attrs->'{attr_value.get('anh_mau')}' ->> 0 as anh_mau,
                attr.attrs->'{attr_value.get('size')}' ->> 0 as size,
                attr.attrs->'{attr_value.get('tai_san_xuat')}' ->> 0 as tai_san_xuat,
                attr.attrs->'{attr_value.get('chat_luong')}' ->> 0 as chat_luong,
                attr.attrs->'{attr_value.get('chat_lieu_vai_chinh')}' ->> 0 as chat_lieu_vai_chinh,
                attr.attrs->'{attr_value.get('subclass1')}' ->> 0 as subclass1,
                attr.attrs->'{attr_value.get('subclass2')}' ->> 0 as subclass2,
                attr.attrs->'{attr_value.get('subclass3')}' ->> 0 as subclass3,
                attr.attrs->'{attr_value.get('subclass4')}' ->> 0 as subclass4,
                attr.attrs->'{attr_value.get('subclass5')}' ->> 0 as subclass5,
                attr.attrs->'{attr_value.get('subclass6')}' ->> 0 as subclass6,
                attr.attrs->'{attr_value.get('subclass7')}' ->> 0 as subclass7,
                attr.attrs->'{attr_value.get('subclass8')}' ->> 0 as subclass8,
                attr.attrs->'{attr_value.get('subclass9')}' ->> 0 as subclass9,
                attr.attrs->'{attr_value.get('subclass10')}' ->> 0 as subclass10,
                attr.attrs->'{attr_value.get('thuoc_tinh1')}' ->> 0 as thuoc_tinh1,
                attr.attrs->'{attr_value.get('thuoc_tinh2')}' ->> 0 as thuoc_tinh2,
                attr.attrs->'{attr_value.get('muc_dich_su_dung')}' ->> 0 as muc_dich_su_dung,
                attr.attrs->'{attr_value.get('nha_thiet_ke')}' ->> 0 as nha_thiet_ke,
                attr.attrs->'{attr_value.get('xuat_xu')}' ->> 0 as xuat_xu,
                attr.attrs->'{attr_value.get('nam_san_xuat')}' ->> 0 as nam_san_xuat,
                attr.attrs->'{attr_value.get('mua_vu')}' ->> 0 as mua_vu,
                attr.attrs->'{attr_value.get('loai_hang_hoa')}' ->> 0 as loai_hang_hoa,
                attr.attrs->'{attr_value.get('nguon_hang')}' ->> 0 as nguon_hang,
                attr.attrs->'{attr_value.get('mau_co_ban')}' ->> 0 as mau_co_ban,
                attr.attrs->'{attr_value.get('mau_phoi')}' ->> 0 as mau_phoi,
                attr.attrs->'{attr_value.get('vung_ban_hang')}' ->> 0 as vung_ban_hang,
                attr.attrs->'{attr_value.get('kich_thuoc')}' ->> 0 as kich_thuoc,
                attr.attrs->'{attr_value.get('san_pham_tach_ma')}' ->> 0 as san_pham_tach_ma,
                attr.attrs->'{attr_value.get('nganh_vai')}' ->> 0 as nganh_vai,
                attr.attrs->'{attr_value.get('mau_cu')}' ->> 0 as mau_cu,
                attr.attrs->'{attr_value.get('kenh_ban_hang')}' ->> 0 as kenh_ban_hang,
                attr.attrs->'{attr_value.get('menh_gia')}' ->> 0 as menh_gia
                from
                    product_product pp
                left join product_template pt on
                    pp.product_tmpl_id = pt.id
                left join uom_uom uu on
                    pt.uom_id = uu.id
                left join uom_uom uu2 on
                    pt.uom_po_id = uu2.id
                left join (
                    select
                        product_id,
                        json_object_agg(attrs_code,
                        value) as attrs
                    from
                        (
                        select
                            pp.id as product_id,
                            pa.attrs_code as attrs_code,
                            array_agg(coalesce(pav.name::json -> 'vi_VN',
                        pav.name::json -> 'en_US')) as value
                        from
                            product_template_attribute_line ptal
                        left join product_product pp on
                            pp.product_tmpl_id = ptal.product_tmpl_id
                        left join product_attribute_value_product_template_attribute_line_rel rel on
                            rel.product_template_attribute_line_id = ptal.id
                        left join product_attribute pa on
                            ptal.attribute_id = pa.id
                        left join product_attribute_value pav on
                            pav.id = rel.product_attribute_value_id
                        where
                            pa.attrs_code is not null
                        group by
                            pp.id,
                            pa.attrs_code
                      ) as att
                    group by
                        product_id
                ) attr on
                    attr.product_id = pp.id
                left join res_brand rb on
                    pt.brand_id = rb.id
                )
                
                SELECT
                    {self.categ_id and field_with_categ_id or field_with_brand_id}
                    pi.*
                FROM
                    category_tree ct
                LEFT JOIN category_tree ct1 ON ct.pc_id = ct1.parent_id
                LEFT JOIN category_tree ct2 ON ct1.pc_id = ct2.parent_id
                LEFT JOIN category_tree ct3 ON ct2.pc_id = ct3.parent_id
                LEFT JOIN category_tree ct4 ON ct3.pc_id = ct4.parent_id
                JOIN product_info pi ON pi.categ_id = {self.categ_id and 'ct.pc_id' or 'ct4.pc_id'}
                where 1 = 1
        """
        if self.product_id:
            query += f" and pp.id = any(array{self.product_id.ids})"
        if self.brand_id:
            query += f" and ct.pc_id = {self.brand_id.id}"
        if self.categ_id:
            query += f" and ct.pc_id = {self.categ_id.id}"
        if self.group_id:
            query += f" and ct1.pc_id = {self.group_id.id}"
        if self.line_id:
            query += f" and ct2.pc_id = {self.line_id.id}"
        if self.structure_id:
            query += f" and ct3.pc_id = {self.structure_id.id}"

        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query(allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo thông tin sản phẩm')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo thông tin sản phẩm', formats.get('header_format'))
        sheet.write(2, 0, 'Sản phẩm: %s' % self.product_id.mapped('name'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        index = 0
        for value in data['data']:
            sheet.write(row, 0, value.get('id'), formats.get('normal_format'))
            sheet.write(row, 1, value.get('barcode'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('sku_code'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('makithuat'), formats.get('center_format'))
            sheet.write(row, 4, value.get('default_code'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('name'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('tenhangcu'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('loai_sp'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('loai_mua_hang'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('cs_tinh_phi'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('cs_kiem_soat'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('thuong_hieu'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('dm_sanpham'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('nhomhang'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('donghang'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('ketcau'), formats.get('normal_format'))
            sheet.write(row, 16, value.get('doi_tuong'), formats.get('normal_format'))
            sheet.write(row, 17, value.get('nhan_hieu'), formats.get('normal_format'))
            sheet.write(row, 18, value.get('donvi'), formats.get('normal_format'))
            sheet.write(row, 19, value.get('dv_muahang'), formats.get('normal_format'))
            sheet.write(row, 20, value.get('don_vi_tinh2'), formats.get('normal_format'))
            sheet.write(row, 21, value.get('hs_quydoi'), formats.get('normal_format'))
            sheet.write(row, 22, value.get('mau_co_ban'), formats.get('normal_format'))
            sheet.write(row, 23, value.get('mau_sac'), formats.get('normal_format'))
            sheet.write(row, 24, value.get('anh_mau'), formats.get('normal_format'))
            sheet.write(row, 25, value.get('mau_phoi'), formats.get('normal_format'))
            sheet.write(row, 26, value.get('pantone'), formats.get('normal_format'))
            sheet.write(row, 27, value.get('mau_ncc'), formats.get('normal_format'))
            sheet.write(row, 28, value.get('mau_cu'), formats.get('normal_format'))
            sheet.write(row, 29, value.get('size'), formats.get('normal_format'))
            sheet.write(row, 30, value.get('daisize'), formats.get('normal_format'))
            sheet.write(row, 31, value.get('kich_thuoc'), formats.get('normal_format'))
            sheet.write(row, 32, value.get('trongluong'), formats.get('normal_format'))
            sheet.write(row, 33, value.get('khovai'), formats.get('normal_format'))
            sheet.write(row, 34, value.get('tai_san_xuat'), formats.get('normal_format'))
            sheet.write(row, 35, value.get('expiration_date'), formats.get('normal_format'))
            sheet.write(row, 36, value.get('warning_date'), formats.get('normal_format'))
            sheet.write(row, 37, value.get('number_days_change_refund'), formats.get('normal_format'))
            sheet.write(row, 38, value.get('chat_luong'), formats.get('normal_format'))
            sheet.write(row, 39, value.get('nam_san_xuat'), formats.get('normal_format'))
            sheet.write(row, 40, value.get('mathietke'), formats.get('normal_format'))
            sheet.write(row, 41, value.get('mota_thietke'), formats.get('normal_format'))
            sheet.write(row, 42, value.get('nganh_vai'), formats.get('normal_format'))
            sheet.write(row, 43, value.get('chat_lieu_vai_chinh'), formats.get('normal_format'))
            sheet.write(row, 44, value.get('material_composition'), formats.get('normal_format'))
            sheet.write(row, 45, value.get('subclass1'), formats.get('normal_format'))
            sheet.write(row, 46, value.get('subclass2'), formats.get('normal_format'))
            sheet.write(row, 47, value.get('subclass3'), formats.get('normal_format'))
            sheet.write(row, 48, value.get('subclass4'), formats.get('normal_format'))
            sheet.write(row, 49, value.get('subclass5'), formats.get('normal_format'))
            sheet.write(row, 50, value.get('subclass6'), formats.get('normal_format'))
            sheet.write(row, 51, value.get('subclass7'), formats.get('normal_format'))
            sheet.write(row, 52, value.get('subclass8'), formats.get('normal_format'))
            sheet.write(row, 53, value.get('subclass9'), formats.get('normal_format'))
            sheet.write(row, 54, value.get('subclass10'), formats.get('normal_format'))
            sheet.write(row, 55, value.get('thuoc_tinh1'), formats.get('normal_format'))
            sheet.write(row, 56, value.get('thuoc_tinh2'), formats.get('normal_format'))
            sheet.write(row, 57, value.get('muc_dich_su_dung'), formats.get('normal_format'))
            sheet.write(row, 58, value.get('bosuutap'), formats.get('normal_format'))
            sheet.write(row, 59, value.get('nha_thiet_ke'), formats.get('normal_format'))
            sheet.write(row, 60, value.get('xuat_xu'), formats.get('normal_format'))
            sheet.write(row, 61, value.get('mua_vu'), formats.get('normal_format'))
            sheet.write(row, 62, value.get('loai_hang_hoa'), formats.get('normal_format'))
            sheet.write(row, 63, value.get('user_manual'), formats.get('normal_format'))
            sheet.write(row, 64, value.get('nguon_hang'), formats.get('normal_format'))
            sheet.write(row, 65, value.get('nhom_sp_dactrung'), formats.get('normal_format'))
            sheet.write(row, 66, value.get('kenh_ban_hang'), formats.get('normal_format'))
            sheet.write(row, 67, value.get('vung_ban_hang'), formats.get('normal_format'))
            sheet.write(row, 68, value.get('tem_nhan'), formats.get('normal_format'))
            sheet.write(row, 69, value.get('ghichu'), formats.get('normal_format'))
            sheet.write(row, 70, value.get('san_pham_tach_ma'), formats.get('normal_format'))
            sheet.write(row, 71, value.get('menh_gia'), formats.get('normal_format'))
            sheet.write(row, 72, value.get('cotheban'), formats.get('normal_format'))
            sheet.write(row, 73, value.get('cothemua'), formats.get('normal_format'))
            sheet.write(row, 74, value.get('khadung_pos'), formats.get('normal_format'))
            row += 1
