# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Mã CN', 'Ngày lập phiếu', 'Ngày HĐ', 'Số HĐ', 'Mã Khách', 'Tên Khách', 'Mã vạch', 'Tên hàng', 'Nhóm hàng', 'Nhãn hiệu',
    'Kích cỡ', 'Màu sắc', 'Đơn vị', 'Dòng hàng', 'Kết cấu', 'Bộ sưu tập', 'SL Bán', 'SL Trả', 'Giá', 'Giảm giá', 'Giảm trên HĐ', 'Thành tiền',
    'Thành tiền NTL', 'Mô tả', 'Hạng', 'Chương trình khuyến mại', 'Mã thẻ GG', 'Voucher', 'Nhân viên', 'Đơn hàng gốc', 'Mã loại', 'Kênh bán'
]


class ReportNum20(models.TransientModel):
    _name = 'report.num20'
    _inherit = 'report.base'
    _description = 'Invoice detail sales and refund'

    lock_date = fields.Date('Lock date')
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_id = fields.Many2one('store', string='Store')
    type = fields.Selection([('store', _('Store')), ('ecommerce', _('Ecommerce'))], string='Sale Type', required=True, default='store')
    customer = fields.Char('Customer-info-x')
    order_filter = fields.Char('Order-filter')

    @api.constrains('from_date', 'to_date', 'lock_date')
    def check_dates(self):
        for record in self:
            if record.lock_date and (record.lock_date > record.from_date):
                raise ValidationError(_('From Date must be greater than or equal Lock Date'))
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand_id(self):
        self.store_id = False

    def _get_query(self, store_ids, allowed_company):
        self.ensure_one()
        tz_offset = self.tz_offset
        user_lang_code = self.env.user.lang
        attr_value = self.env['res.utility'].get_attribute_code_config()

        customer_condition = f"and (rp.ref ilike '%{self.customer}%' or rp.phone ilike '%{self.customer}%')" if self.customer else ''
        order_filter_condition = f"""and (po.pos_reference ilike '%{self.order_filter}%'
             or po.id in (select order_id from pos_order_line where product_id in (
                select id from product_product where default_code ilike '%{self.order_filter}%'))
             or po.id in (select order_id from promotion_usage_line where code_id in(
                select id from promotion_code where name ilike '%{self.order_filter}%')))""" if self.order_filter else ''
        query = f"""
WITH account_by_categ_id as ( -- lấy mã tài khoản định giá tồn kho bằng cate_id
    select 
        cate.id as cate_id,
        aa.code as account_code
    from product_category cate
        left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
        left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
    where  ir.name='property_stock_valuation_account_id' and ir.company_id = any(array{allowed_company})
    order by cate.id 
),
attribute_data as (
    select product_id                         as product_id,
           json_object_agg(attrs_code, value) as attrs
    from (
        select 
            pp.id                                                                                   as product_id,
            pa.attrs_code                                                                           as attrs_code,
            array_agg(coalesce(pav.name::json -> '{user_lang_code}', pav.name::json -> 'en_US'))    as value
        from product_template_attribute_line ptal
            left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
            left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
            left join product_attribute pa on ptal.attribute_id = pa.id
            left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
        where pa.attrs_code notnull
        group by pp.id, pa.attrs_code) as att
    group by product_id
)
select
    row_number() over (order by po.id)                                          as num,
    sto.code                                                                    as ma_cn,
    to_char(po.create_date + '{tz_offset} h'::interval, 'DD/MM/YYYY')           as ngay_lap_phieu,
    to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY')            as ngay_hd,
    po.pos_reference                                                            as so_hd,
    rp.ref                                                                      as ma_kh,
    rp.name                                                                     as ten_kh,
    pp.barcode                                                                  as ma_vach,
    pol.full_product_name                                                       as ten_hang,
    split_part(pc.complete_name, ' / ', 2)                                      as nhom_hang,
    ad.attrs::json -> '{attr_value.get('nhan_hieu', '')}'                       as nhan_hieu,
    ad.attrs::json -> '{attr_value.get('size', '')}'                            as kich_co,
    ad.attrs::json -> '{attr_value.get('mau_sac', '')}'                         as mau_sac,
    coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US')   as don_vi,
    split_part(pc.complete_name, ' / ', 3)                                      as dong_hang,
    split_part(pc.complete_name, ' / ', 4)                                      as ket_cau,
    pt.collection                                                               as bo_suu_tap,
    greatest(pol.qty, 0)                                                        as sl_ban,
    abs(least(pol.qty, 0))                                                      as sl_tra,
    coalesce(pol.original_price, 0)                                             as gia,
    coalesce((select sum(
            case when type = 'point' then recipe * 1000
                when type = 'card' then recipe
                when type = 'ctkm' then discounted_amount
                else 0
            end
        ) from pos_order_line_discount_details where pos_order_line_id = pol.id), 0) as giam_gia,
    0                                                                           as giam_tren_hd,
    po.note                                                                     as mo_ta,
    cr.name                                                                     as hang,
    (select array_agg(name) from (
        select distinct name from promotion_program where id in (
            select program_id from promotion_usage_line where order_line_id = pol.id
            )) as xx)                                                           as ctkm,
    (select array_agg(name) from (
        select distinct name from promotion_code where id in (
            select code_id from promotion_usage_line where order_line_id = pol.id
            )) as xx)                                                           as ma_the_gg,
    (select array_agg(name) from (
        select distinct name from voucher_voucher where id in (
            select voucher_id from pos_voucher_line where pos_order_id = po.id
            )) as xx)                                                           as voucher,
    emp.name                                                                    as nhan_vien,        
    (select pos_reference from pos_order where id in (
        select order_id from pos_order_line
         where id = pol.refunded_orderline_id
    ))                                                                          as don_hang_goc,
    acc.account_code                                                            as ma_loai,
    ''                                                                          as kenh_ban
from pos_order po
    join pos_order_line pol on pol.order_id = po.id
    join product_product pp on pp.id = pol.product_id
    join product_template pt on pt.id = pp.product_tmpl_id
    left join uom_uom uom on uom.id = pt.uom_id
    left join product_category pc on pc.id = pt.categ_id
    left join res_partner rp on po.partner_id = rp.id
    left join pos_session ses on ses.id = po.session_id
    left join pos_config conf on conf.id = ses.config_id
    left join store sto on sto.id = conf.store_id
    left join partner_card_rank pcr on pcr.customer_id = rp.id and pcr.brand_id = {self.brand_id.id}
    left join card_rank cr on cr.id = pcr.card_rank_id
    left join hr_employee emp on emp.id = pol.employee_id
    left join account_by_categ_id acc on acc.cate_id = pc.id
    left join attribute_data ad on ad.product_id = pp.id
where  po.company_id = any( array{allowed_company}) and pt.detailed_type <> 'service' and pt.voucher <> true
    and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
    and sto.id = any(array{store_ids})
    {customer_condition}
    {order_filter_condition}
order by num
"""
        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        store_ids = (self.env['store'].search([('brand_id', '=', self.brand_id.id)]).ids or [-1]) if not self.store_id else self.store_id.ids
        query = self._get_query(store_ids, allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Chi tiết hóa đơn bán - đổi - trả')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Bảng kê chi tiết hóa đơn bán - đổi - trả', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày: %s đến ngày: %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ma_cn'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ngay_lap_phieu'), formats.get('center_format'))
            sheet.write(row, 3, value.get('ngay_hd'), formats.get('center_format'))
            sheet.write(row, 4, value.get('so_hd'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('ma_kh'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ten_kh'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('ma_vach'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('ten_hang'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 10, ', '.join(value.get('nhan_hieu') or []), formats.get('normal_format'))
            sheet.write(row, 11, ', '.join(value.get('kich_co') or []), formats.get('normal_format'))
            sheet.write(row, 12, ', '.join(value.get('mau_sac') or []), formats.get('normal_format'))
            sheet.write(row, 13, value.get('don_vi'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 16, value.get('bo_suu_tap'), formats.get('normal_format'))
            sheet.write(row, 17, value.get('sl_ban', 0), formats.get('int_number_format'))
            sheet.write(row, 18, value.get('sl_tra', 0), formats.get('int_number_format'))
            sheet.write(row, 19, value.get('gia', 0), formats.get('int_number_format'))
            sheet.write(row, 20, value.get('giam_gia', 0), formats.get('int_number_format'))
            sheet.write(row, 21, value.get('giam_tren_hd', 0), formats.get('int_number_format'))
            sheet.write(row, 22, value.get('gia', 0) * value.get('sl_ban', 0) - value.get('giam_gia', 0), formats.get('int_number_format'))
            sheet.write(row, 23, value.get('gia', 0) * value.get('sl_tra', 0), formats.get('int_number_format'))
            sheet.write(row, 24, value.get('mo_ta'), formats.get('normal_format'))
            sheet.write(row, 25, value.get('hang'), formats.get('normal_format'))
            sheet.write(row, 26, ', '.join(value.get('ctkm') or []), formats.get('normal_format'))
            sheet.write(row, 27, ', '.join(value.get('ma_the_gg') or []), formats.get('normal_format'))
            sheet.write(row, 28, ', '.join(value.get('voucher') or []), formats.get('normal_format'))
            sheet.write(row, 29, value.get('nhan_vien'), formats.get('normal_format'))
            sheet.write(row, 30, value.get('don_hang_goc'), formats.get('normal_format'))
            sheet.write(row, 31, value.get('ma_loai'), formats.get('normal_format'))
            sheet.write(row, 32, value.get('kenh_ban'), formats.get('normal_format'))
            row += 1
