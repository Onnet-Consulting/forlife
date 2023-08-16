# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Mã chi nhánh', 'Chi nhánh', 'Ngày lập phiếu', 'Ngày HĐ', 'Số HĐ', 'Mã khách', 'Tên khách', 'Mã vạch', 'Tên hàng', 'Nhóm hàng', 'Nhãn hiệu',
    'Kích cỡ', 'Màu sắc', 'Đơn vị', 'Dòng hàng', 'Kết cấu', 'Bộ sưu tập', 'Số lượng bán', 'Số lượng trả', 'Giá', 'Giảm giá', 'Giảm trên HĐ', 'Thành tiền',
    'Thành tiền NTL', 'Mô tả', 'Hạng', 'Chương trình khuyến mại', 'Mã thẻ GG', 'Voucher', 'Nhân viên', 'Đơn hàng gốc', 'Mã loại', 'Kênh bán',
]


class ReportNum35(models.TransientModel):
    _name = 'report.num35'
    _inherit = ['report.base']
    _description = 'Bảng kê chi tiết hóa đơn TMĐT'

    lock_date = fields.Date('Lock date')
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    customer = fields.Char('Customer-info')
    order_filter = fields.Char('SO-filter')
    nhanh_order = fields.Char('Nhanh order')

    @api.constrains('from_date', 'to_date', 'lock_date')
    def check_dates(self):
        for record in self:
            if record.lock_date and (record.lock_date > record.from_date):
                raise ValidationError(_('From Date must be greater than or equal Lock Date'))
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand_id(self):
        self.warehouse_id = self.warehouse_id.filtered(lambda f: f.brand_id == self.brand_id)

    def _get_query(self, warehouse_ids, allowed_company):
        self.ensure_one()
        tz_offset = self.tz_offset
        user_lang_code = self.env.user.lang
        attr_value = self.env['res.utility'].get_attribute_code_config()
        customer_join = f"""join res_partner rp on so.order_partner_id = rp.id and (rp.ref ilike '%{self.customer}%' or
            rp.name ilike '%{self.customer}%' or rp.phone ilike '%{self.customer}%')""" if self.customer else \
            'left join res_partner rp on so.order_partner_id = rp.id'
        so_filter_condition = f"""and so.name ilike '%{self.order_filter}%'""" if self.order_filter else ''
        nhanh_order_condition = f"""and so.nhanh_id ilike '%{self.nhanh_order}%'""" if self.nhanh_order else ''

        query = f"""
with account_by_categ_id as (select cate.id as cate_id,
                                    aa.code as account_code
                             from product_category cate
                                      left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
                                      left join account_account aa on concat('account.account,', aa.id) = ir.value_reference
                             where ir.name = 'property_stock_valuation_account_id'
                               and ir.company_id = any (array {allowed_company})
                             order by cate.id),
     attribute_data as (select product_id                         as product_id,
                               json_object_agg(attrs_code, value) as attrs
                        from (select pp.id                                                                       as product_id,
                                     pa.attrs_code                                                               as attrs_code,
                                     array_agg(coalesce(pav.name::json ->> '{user_lang_code}', pav.name::json ->> 'en_US')) as value
                              from product_template_attribute_line ptal
                                       left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
                                       left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
                                       left join product_attribute pa on ptal.attribute_id = pa.id
                                       left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
                              where pa.attrs_code notnull
                              group by pp.id, pa.attrs_code) as att
                        group by product_id)
select row_number() over (order by so.id)                                          as stt,
       wh.code                                                                     as ma_cn,
       wh.name                                                                     as ten_cn,
       to_char(so.create_date + interval '{tz_offset} h', 'DD/MM/YYYY')            as ngay_lp,
       to_char(so.date_order + interval '{tz_offset} h', 'DD/MM/YYYY')             as ngay_hd,
       so.name                                                                     as so_hd,
       rp.ref                                                                      as ma_khach,
       rp.name                                                                     as ten_khach,
       pp.barcode                                                                  as ma_vach,
       coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')   as ten_hang,
       split_part(pc.complete_name, ' / ', 2)                                      as nhom_hang,
       ad.attrs::json -> '{attr_value.get('nhan_hieu', '')}'                       as nhan_hieu,
       ad.attrs::json -> '{attr_value.get('size', '')}'                            as kich_co,
       ad.attrs::json -> '{attr_value.get('mau_sac', '')}'                         as mau_sac,
       coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US') as don_vi,
       split_part(pc.complete_name, ' / ', 3)                                      as dong_hang,
       split_part(pc.complete_name, ' / ', 4)                                      as ket_cau,
       pt.collection                                                               as bo_suu_tap,
       case when so.x_is_return = true then 0 else sol.product_uom_qty end         as sl_ban,
       case when so.x_is_return = true then sol.product_uom_qty else 0 end         as sl_tra,
       0                                                                           as gia,
       coalesce((select sum(sop.value)
                 from sale_order_promotion sop
                 where sop.order_line_id = sol.id
                   and sop.product_id = sol.product_id), 0)                        as giam_gia,
       0                                                                           as giam_tren_hd,
       0 * sol.product_uom_qty                                                     as tt_chua_tru_gg,
       case when so.x_is_return = true then 0 * sol.product_uom_qty else 0 end     as tt_ntl_chua_tru_gg,
       ''                                                                          as mo_ta,
       ''                                                                          as hang,
       (select array_agg(sop.description)
        from sale_order_promotion sop
        where sop.order_line_id = sol.id
          and sop.product_id = sol.product_id)                                     as ctkm,
       ''                                                                          as ma_the_gg,
       so.x_code_voucher                                                           as voucher,
       rp1.name                                                                    as nhan_vien,
       so.nhanh_origin_id                                                          as don_hang_goc,
       abci.account_code                                                           as ma_loai,
       'TMĐT'                                                                      as kenh_ban
from sale_order so
         join sale_order_line sol on so.id = sol.order_id
         join stock_location sl on so.x_location_id = sl.id
         join stock_warehouse wh on sl.warehouse_id = wh.id
         {customer_join}
         join product_product pp on sol.product_id = pp.id
         join product_template pt on pp.product_tmpl_id = pt.id
         left join product_category pc on pt.categ_id = pc.id
         left join attribute_data ad on ad.product_id = sol.product_id
         left join uom_uom uom on sol.product_uom = uom.id
         join res_users ru on so.user_id = ru.id
         left join res_partner rp1 on ru.partner_id = rp1.id
         left join account_by_categ_id abci on pt.categ_id = abci.cate_id
where so.source_record = true {so_filter_condition} {nhanh_order_condition}
    and so.company_id = any(array{allowed_company})
    and sl.warehouse_id = any(array{warehouse_ids})
    and {format_date_query("so.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
        """
        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        warehouse_ids = (self.env['stock.warehouse'].search(
            [('brand_id', '=', self.brand_id.id), ('company_id', 'in', allowed_company)]).ids or [-1]
                         ) if not self.warehouse_id else self.warehouse_id.ids
        query = self._get_query(warehouse_ids, allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Bảng kê chi tiết hóa đơn TMĐT')
        sheet.set_row(0, 25)
        sheet.set_row(4, 30)
        sheet.write(0, 0, 'Bảng kê chi tiết hóa đơn TMĐT', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày: %s đến ngày: %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ma_cn'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ten_cn'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ngay_lp'), formats.get('center_format'))
            sheet.write(row, 4, value.get('ngay_hd'), formats.get('center_format'))
            sheet.write(row, 5, value.get('so_hd'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ma_khach'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('ten_khach'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('ma_vach'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('ten_hang'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('ma_the_gg'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 12, ', '.join(value.get('nhan_hieu') or []), formats.get('normal_format'))
            sheet.write(row, 13, ', '.join(value.get('kick_co') or []), formats.get('normal_format'))
            sheet.write(row, 14, ', '.join(value.get('mau_sac') or []), formats.get('normal_format'))
            sheet.write(row, 15, value.get('don_vi'), formats.get('normal_format'))
            sheet.write(row, 16, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 17, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 18, value.get('bo_suu_tap'), formats.get('normal_format'))
            sheet.write(row, 19, value.get('sl_ban'), formats.get('int_number_format'))
            sheet.write(row, 20, value.get('sl_tra'), formats.get('int_number_format'))
            sheet.write(row, 21, value.get('gia', 0), formats.get('int_number_format'))
            sheet.write(row, 22, value.get('giam_gia', 0), formats.get('int_number_format'))
            sheet.write(row, 23, value.get('giam_tren_hd', 0), formats.get('int_number_format'))
            sheet.write(row, 24, value.get('tt_chua_tru_gg', 0) - value.get('giam_gia', 0), formats.get('int_number_format'))
            sheet.write(row, 25, value.get('tt_ntl_chua_tru_gg', 0) - value.get('giam_gia', 0), formats.get('int_number_format'))
            sheet.write(row, 26, value.get('mo_ta'), formats.get('normal_format'))
            sheet.write(row, 27, value.get('hang'), formats.get('normal_format'))
            sheet.write(row, 28, ', '.join(value.get('ctkm') or []), formats.get('normal_format'))
            sheet.write(row, 29, value.get('ma_the_gg'), formats.get('center_format'))
            sheet.write(row, 30, value.get('voucher'), formats.get('normal_format'))
            sheet.write(row, 31, value.get('nhan_vien'), formats.get('normal_format'))
            sheet.write(row, 32, value.get('don_hang_goc'), formats.get('normal_format'))
            sheet.write(row, 33, value.get('ma_loai'), formats.get('normal_format'))
            sheet.write(row, 34, value.get('kenh_ban'), formats.get('normal_format'))
            row += 1
