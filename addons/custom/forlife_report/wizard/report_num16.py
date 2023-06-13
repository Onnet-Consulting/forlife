# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

TITLES = [
    'STT', 'Ngày', 'Số CT', 'Kho', 'Số CT2', 'Kho2', 'Mã khách', 'Tên khách', 'Đối tượng', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu',
    'Mã vạch', 'Mã hàng', 'Tên hàng', 'Màu sắc', 'Kích cỡ', 'Năm sản xuất', 'Bộ sưu tập', 'Xuất xứ', 'Subclass 1', 'Subclass 2',
    'Subclass 3', 'Subclass 4', 'Subclass 5', 'Đơn vị tính', 'Nhập', 'Xuất', 'Mã loại', 'Ngày tờ khai', 'Diễn giải',
]


class ReportNum16(models.TransientModel):
    _name = 'report.num16'
    _inherit = 'report.base'
    _description = 'Report stock move'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    product_domain = fields.Char('Product', default='[]')
    warehouse_domain = fields.Char('Warehouse', default='[]')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self, product_ids, warehouse_ids, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        attr_value = self.env['res.utility'].get_attribute_code_config()

        where_query = f""" where
            sm.company_id = any( array{allowed_company})
            and sm.state = 'done'
            and {format_date_query("sm.date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
            and sm.product_id = any (array{product_ids})
            and (src_wh.id = any (array{warehouse_ids}) or des_wh.id = any (array{warehouse_ids}))
        """

        query = f"""
with account_by_categ_id as ( -- lấy mã tài khoản định giá tồn kho bằng cate_id
    select 
        cate.id as cate_id,
        aa.code as account_code
    from product_category cate
        left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
        left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
    where  ir.name='property_stock_valuation_account_id' and ir.company_id = any( array{allowed_company})
    order by cate.id 
),
attribute_data as (
    select 
        pp.id                                                                                   as product_id,
        pa.attrs_code                                                                           as attrs_code,
        array_agg(coalesce(pav.name::json -> '{user_lang_code}', pav.name::json -> 'en_US'))    as value
    from product_template_attribute_line ptal
    left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
    left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
    left join product_attribute pa on ptal.attribute_id = pa.id
    left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
    where pp.id = any (array{product_ids}) 
    group by pp.id, pa.attrs_code
),
product_cate_info as (
    select 
        pp.id     		                                                          as product_id,
        cate.complete_name                                                        as complete_name,
        pp.barcode                                                                as product_barcode,
        pp.default_code                                                           as internal_ref,
        coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US')   as product_name,
        acc.account_code                                                          as account_code,
        pt.collection                                                             as bo_suu_tap,
        doi_tuong.value as doi_tuong,
        mau_sac.value as mau_sac,
        kich_thuoc.value as kich_thuoc,
        nam_sx.value as nam_sx,
        xuat_xu.value as xuat_xu,
        subclass1.value as subclass1,
        subclass2.value as subclass2,
        subclass3.value as subclass3,
        subclass4.value as subclass4,
        subclass5.value as subclass5
    from product_product pp 
        left join product_template pt on pt.id = pp.product_tmpl_id
        join product_category cate on cate.id = pt.categ_id
        left join account_by_categ_id acc on acc.cate_id = cate.id
        left join attribute_data doi_tuong on doi_tuong.product_id = pp.id and doi_tuong.attrs_code = '{attr_value.get('doi_tuong', '')}'
        left join attribute_data mau_sac on mau_sac.product_id = pp.id and mau_sac.attrs_code = '{attr_value.get('mau_sac', '')}'
        left join attribute_data kich_thuoc on kich_thuoc.product_id = pp.id and kich_thuoc.attrs_code = '{attr_value.get('size', '')}'
        left join attribute_data nam_sx on nam_sx.product_id = pp.id and nam_sx.attrs_code = '{attr_value.get('nam_san_xuat', '')}'
        left join attribute_data xuat_xu on xuat_xu.product_id = pp.id and xuat_xu.attrs_code = '{attr_value.get('xuat_xu', '')}'
        left join attribute_data subclass1 on subclass1.product_id = pp.id and subclass1.attrs_code = '{attr_value.get('subclass1', '')}'
        left join attribute_data subclass2 on subclass2.product_id = pp.id and subclass2.attrs_code = '{attr_value.get('subclass2', '')}'
        left join attribute_data subclass3 on subclass3.product_id = pp.id and subclass3.attrs_code = '{attr_value.get('subclass3', '')}'
        left join attribute_data subclass4 on subclass4.product_id = pp.id and subclass4.attrs_code = '{attr_value.get('subclass4', '')}'
        left join attribute_data subclass5 on subclass5.product_id = pp.id and subclass5.attrs_code = '{attr_value.get('subclass5', '')}'
    where pp.id = any (array{product_ids})
)
select row_number() over ()                                                         as num,
       to_char(sm.date, 'DD/MM/YYYY')                                               as date,
       ''                                                                           as so_ct,
       ''                                                                           as wh_name,
       ''                                                                           as so_ct2,
       ''                                                                           as wh_name2,
       ''                                                                           as ma_khach,
       ''                                                                           as ten_khach,
       pci.doi_tuong                                                                as doi_tuong,
       split_part(pci.complete_name, ' / ', 2)                                      as nhom_hang,
       split_part(pci.complete_name, ' / ', 3)                                      as dong_hang,
       split_part(pci.complete_name, ' / ', 4)                                      as ket_cau,
       pci.product_barcode                                                          as ma_vach,
       pci.internal_ref                                                             as ma_hang,
       pci.product_name                                                             as ten_hang,
       pci.mau_sac                                                                  as mau_sac,
       pci.kich_thuoc                                                               as kich_co,
       pci.nam_sx                                                                   as nam_sx,
       pci.bo_suu_tap                                                               as bo_suu_tap,
       pci.xuat_xu                                                                  as xuat_xu,
       pci.subclass1                                                                as subclass1,
       pci.subclass2                                                                as subclass2,
       pci.subclass3                                                                as subclass3,
       pci.subclass4                                                                as subclass4,
       pci.subclass5                                                                as subclass5,
       coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US')    as dv_tinh,
       sm.quantity_done                                                             as nhap,
       sm.quantity_done                                                             as xuat,
       pci.account_code                                                             as ma_loai,
       ''                                                                           as ngay_to_khai,
       sm.name                                                                      as dien_giai
from stock_move sm
    left join uom_uom uom on uom.id = sm.product_uom
    left join stock_location des_lc on sm.location_dest_id = des_lc.id
    left join stock_warehouse des_wh on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
    left join stock_location src_lc on sm.location_id = src_lc.id
    left join stock_warehouse src_wh on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
    left join product_cate_info pci on pci.product_id = sm.product_id
{where_query}
order by num
"""
        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        product_ids = self.env['product.product'].search(safe_eval(self.product_domain)).ids or [-1]
        warehouse_ids = self.env['stock.warehouse'].search(safe_eval(self.warehouse_domain) + [('company_id', 'in', allowed_company)]).ids or [-1]
        query = self._get_query(product_ids, warehouse_ids, allowed_company)
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo chi tiết xuất nhập hàng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo chi tiết xuất nhập hàng', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày %s' % self.from_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 2, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('date'), formats.get('center_format'))
            sheet.write(row, 2, value.get('so_ct'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('wh_name'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('so_ct2'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('wh_name2'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ma_khach'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('ten_khach'), formats.get('normal_format'))
            sheet.write(row, 8, ', '.join(value.get('doi_tuong') or []), formats.get('normal_format'))
            sheet.write(row, 9, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('ma_vach'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('ma_hang'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('ten_hang'), formats.get('normal_format'))
            sheet.write(row, 15, ', '.join(value.get('mau_sac') or []), formats.get('normal_format'))
            sheet.write(row, 16, ', '.join(value.get('kich_co') or []), formats.get('normal_format'))
            sheet.write(row, 17, ', '.join(value.get('nam_sx') or []), formats.get('normal_format'))
            sheet.write(row, 18, value.get('bo_suu_tap'), formats.get('normal_format'))
            sheet.write(row, 19, ', '.join(value.get('xuat_xu') or []), formats.get('normal_format'))
            sheet.write(row, 20, ', '.join(value.get('subclass1') or []), formats.get('normal_format'))
            sheet.write(row, 21, ', '.join(value.get('subclass2') or []), formats.get('normal_format'))
            sheet.write(row, 22, ', '.join(value.get('subclass3') or []), formats.get('normal_format'))
            sheet.write(row, 23, ', '.join(value.get('subclass4') or []), formats.get('normal_format'))
            sheet.write(row, 24, ', '.join(value.get('subclass5') or []), formats.get('normal_format'))
            sheet.write(row, 25, value.get('dv_tinh'), formats.get('normal_format'))
            sheet.write(row, 26, value.get('nhap'), formats.get('normal_format'))
            sheet.write(row, 27, value.get('xuat'), formats.get('normal_format'))
            sheet.write(row, 28, value.get('ma_loai'), formats.get('normal_format'))
            sheet.write(row, 29, value.get('ngay_to_khai'), formats.get('normal_format'))
            sheet.write(row, 30, value.get('dien_giai'), formats.get('normal_format'))
            row += 1
