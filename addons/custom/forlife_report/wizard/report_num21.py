# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

TITLES = [
    'STT', 'Trạng thái', 'Ngày HĐ', 'Số HĐ', 'Mã kho xuất', 'Kho xuất', 'Mã kho nhận', 'Kho nhận', 'Đơn vị tính', 'Mã vạch',
    'Mã hàng', 'Tên hàng', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu', 'Quy ước dòng hàng', 'Màu sắc', 'Kích cỡ', 'Diễn giải', 'Bộ sưu tập',
    'Kiểu dáng', 'Số lượng', 'Giá', 'Thành tiền', 'TK kho', 'TK giá vốn', 'Ngày tạo', 'Mã phiếu', 'Tên phiếu', 'Đối tượng', 'Năm sản xuất'
]


class ReportNum21(models.TransientModel):
    _name = 'report.num21'
    _inherit = 'report.base'
    _description = 'Report stock transfer'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    location_province_ids = fields.Many2many('res.location.province', string='Location Province')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    product_domain = fields.Char('Product', default='[]')
    is_all = fields.Boolean(_('All'), default=False)
    is_delivery = fields.Boolean(_('Delivery'), default=False)
    is_receive = fields.Boolean(_('Receive'), default=False)
    is_done = fields.Boolean(_('Done'), default=False)

    @api.onchange('location_province_ids')
    def onchange_location_province(self):
        self.warehouse_ids = self.warehouse_ids.filtered(lambda f: f.loc_province_id.id in (self.location_province_ids.ids or [False]))

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

        status = []
        if self.is_all or (not self.is_all and not self.is_delivery and not self.is_receive and not self.is_done):
            status = ['out_approve', 'in_approve', 'done']
        else:
            if self.is_delivery:
                status.append('out_approve')
            if self.is_receive:
                status.append('in_approve')
            if self.is_done:
                status.append('done')

        query = f"""
with acc_whs as (
    select 
        cate.id as cate_id,
        aa.code as acc_wh
    from product_category cate
        left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
        left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
    where  ir.name='property_stock_valuation_account_id' and ir.company_id = any(array{allowed_company})
    order by cate.id
),
acc_cost as (
    select 
        cate.id as cate_id,
        aa.code as acc_cst
    from product_category cate
        left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
        left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
    where  ir.name='property_stock_account_output_categ_id' and ir.company_id = any(array{allowed_company})
    order by cate.id
),
account_by_categ_id as (
    select 
        coalesce(acc_whs.cate_id, acc_cost.cate_id) as cate_id,
        acc_whs.acc_wh as acc_wh,
        acc_cost.acc_cst as acc_cost
    from acc_whs
    full outer join acc_cost on acc_whs.cate_id = acc_cost.cate_id
),
attribute_data as (
    select product_id                         as product_id,
           json_object_agg(attrs_code, value) as attrs
    from (
        select 
            pp.id                                                                                   as product_id,
            pa.attrs_code                                                                           as attrs_code,
            array_agg(coalesce(pav.name::json ->> '{user_lang_code}', pav.name::json ->> 'en_US'))    as value
        from product_template_attribute_line ptal
            left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
            left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
            left join product_attribute pa on ptal.attribute_id = pa.id
            left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
        where pp.id = any (array{product_ids}) and pa.attrs_code notnull
        group by pp.id, pa.attrs_code) as att
    group by product_id
),
prepare_data_tb as (
    select '{{"out_approve":"Xác nhận xuất","in_approve":"Xác nhận nhập","done":"Hoàn thành"}}'::json as status
)
select 
    row_number() over (order by st.id)                                          as num,
    (select status::json ->> st.state from prepare_data_tb)                      as trang_thai,
    ''                                                                          as ngay_hd,
    st.name                                                                     as so_hd,
    s_loc.code                                                                  as ma_kho_xuat,
    s_loc.name                                                                  as kho_xuat,
    d_loc.code                                                                  as ma_kho_nhan,
    d_loc.name                                                                  as kho_nhan,
    coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')   as don_vi_tinh,
    pp.barcode                                                                  as ma_vach,
    pp.default_code                                                             as ma_hang,
    coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')     as ten_hang,
    split_part(pc.complete_name, ' / ', 2)                                      as nhom_hang,
    split_part(pc.complete_name, ' / ', 3)                                      as dong_hang,
    split_part(pc.complete_name, ' / ', 4)                                      as ket_cau,
    case when pc.name ilike '%%hàng hóa%%' then 'Nhập mua'
        when pc.name ilike '%%thành phẩm%%' then 'Sản xuất' else ''
    end                                                                         as quy_uoc_dong_hang,
    ad.attrs::json ->> '{attr_value.get('mau_sac', '')}'                         as mau_sac,
    ad.attrs::json ->> '{attr_value.get('size', '')}'                            as kich_co,
    ''                                                                          as dien_giai,
    pt.collection                                                               as bo_suu_tap,
    ad.attrs::json ->> '{attr_value.get('subclass1', '')}'                       as kieu_dang,
    case when st.state = 'out_approve' then stl.qty_out
        when st.state in ('in_approve', 'done') then stl.qty_in
        else 0 end                                                              as so_luong,
    pt.list_price                                                               as gia,
    acc.acc_wh                                                                  as tk_kho,
    acc.acc_cost                                                                as tk_gia_von,
    to_char(pp.create_date + interval '{tz_offset} hours', 'DD/MM/YYYY')        as ngay_tao,
    substr(st.name, 0, 4)                                                       as ma_phieu,
    'Phiếu xuất nội bộ'                                                         as ten_phieu,
    ad.attrs::json ->> '{attr_value.get('doi_tuong', '')}'                       as doi_tuong,
    ad.attrs::json ->> '{attr_value.get('nam_san_xuat', '')}'                    as nam_sx
from stock_transfer st
    join stock_transfer_line stl on stl.stock_transfer_id = st.id
    left join stock_location s_loc on s_loc.id = st.location_id
    left join stock_location d_loc on d_loc.id = st.location_dest_id
    left join uom_uom uom on uom.id = stl.uom_id
    left join product_product pp on pp.id = stl.product_id
    left join product_template pt on pt.id = product_tmpl_id
    left join product_category pc on pc.id = pt.categ_id
    left join account_by_categ_id acc on acc.cate_id = pc.id
    left join attribute_data ad on ad.product_id = stl.product_id    
where {format_date_query("st.create_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
    and stl.product_id = any (array{product_ids})
    and (s_loc.warehouse_id = any (array{warehouse_ids}) or d_loc.warehouse_id = any (array{warehouse_ids}))
    and st.state = any(array{status})
order by num
"""
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        allowed_company = allowed_company or [-1]
        values = dict(super().get_data(allowed_company))
        product_ids = self.env['product.product'].search(safe_eval(self.product_domain)).ids or [-1]
        if not self.location_province_ids:
            warehouse_ids = self.env['stock.warehouse'].search([('company_id', 'in', allowed_company), ('loc_province_id', '=', False)]).ids or [-1]
        else:
            warehouse_ids = self.warehouse_ids.ids if self.warehouse_ids else (self.env['stock.warehouse'].search([
                ('company_id', 'in', allowed_company), ('loc_province_id', 'in', self.location_province_ids.ids)]).ids or [-1])
        query = self._get_query(product_ids, warehouse_ids, allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo chi tiết hàng hóa luân chuyển')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo chi tiết hàng hóa luân chuyển', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày %s' % self.from_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 2, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('trang_thai'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ngay_hd'), formats.get('center_format'))
            sheet.write(row, 3, value.get('so_hd'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ma_kho_xuat'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('kho_xuat'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ma_kho_nhan'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('kho_nhan'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('don_vi_tinh'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('ma_vach'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('ma_hang'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('ten_hang'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('quy_uoc_dong_hang'), formats.get('normal_format'))
            sheet.write(row, 16, ', '.join(value.get('mau_sac') or []), formats.get('normal_format'))
            sheet.write(row, 17, ', '.join(value.get('kich_co') or []), formats.get('normal_format'))
            sheet.write(row, 18, value.get('dien_giai'), formats.get('normal_format'))
            sheet.write(row, 19, value.get('bo_suu_tap'), formats.get('normal_format'))
            sheet.write(row, 20, ', '.join(value.get('kieu_dang') or []), formats.get('normal_format'))
            sheet.write(row, 21, value.get('so_luong') or 0, formats.get('int_number_format'))
            sheet.write(row, 22, value.get('gia') or 0, formats.get('int_number_format'))
            sheet.write(row, 23, value.get('so_luong', 0) * value.get('gia', 0), formats.get('int_number_format'))
            sheet.write(row, 24, value.get('tk_kho'), formats.get('normal_format'))
            sheet.write(row, 25, value.get('tk_gia_von'), formats.get('normal_format'))
            sheet.write(row, 26, value.get('ngay_tao'), formats.get('center_format'))
            sheet.write(row, 27, value.get('ma_phieu'), formats.get('normal_format'))
            sheet.write(row, 28, value.get('ten_phieu'), formats.get('normal_format'))
            sheet.write(row, 29, ', '.join(value.get('doi_tuong') or []), formats.get('normal_format'))
            sheet.write(row, 30, ', '.join(value.get('nam_sx') or []), formats.get('normal_format'))
            row += 1
