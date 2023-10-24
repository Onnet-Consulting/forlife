# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Mã CN', 'Tên CN', 'Ngày lập phiếu', 'Ngày HĐ', 'Số HĐ', 'Mã Khách', 'Số điện thoại', 'Tên Khách', 'Mã vạch', 'Tên hàng',
    'Nhóm hàng', 'Nhãn hiệu', 'Kích cỡ', 'Màu sắc', 'Đơn vị', 'Dòng hàng', 'Kết cấu', 'Bộ sưu tập', 'SL Bán', 'SL Trả', 'Giá', 'Giảm giá',
    'Giảm trên HĐ', 'Thành tiền', 'Thành tiền NTL', 'Mô tả', 'Hạng', 'Chương trình khuyến mại', 'Mã thẻ GG', 'Voucher', 'Nhân viên',
    'Đơn hàng gốc', 'Ngày đơn hàng gốc', 'Mã loại', 'Kênh bán'
]


class ReportNum20(models.TransientModel):
    _name = 'report.num20'
    _inherit = 'report.base'
    _description = 'Bảng kê chi tiết hóa đơn bán - đổi - trả'

    lock_date = fields.Date('Lock date')
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_ids = fields.Many2many('store', string='Store')
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
        self.store_ids = self.store_ids.filtered(lambda f: f.brand_id.id == self.brand_id.id)

    def _get_query(self, store_ids, allowed_company):
        self.ensure_one()
        tz_offset = self.tz_offset
        user_lang_code = self.env.user.lang
        attr_value = self.env['res.utility'].get_attribute_code_config()

        customer_condition = f"and (rp.ref ilike '%%{self.customer}%%' or rp.phone ilike '%%{self.customer}%%' or rp.name ilike '%%{self.customer}%%')" if self.customer else ''
        order_filter_condition = f"""and (po.name ilike '%%{self.order_filter}%%' or pp.default_code ilike '%%{self.order_filter}%%' or pc.name ilike '%%{self.order_filter}%%')""" if self.order_filter else ''
        left_join_table = ("left join promotion_usage_line pul on po.id = pul.order_id\n"
                           "left join promotion_code pc on pc.id = pul.code_id") if self.order_filter else ''

        query = f"""
with pol_datas as (select pol.id                                                           as pol_id,
                          po.id                                                            as po_id,
                          po.name                                                          as so_hd,
                          po.note                                                          as mo_ta,
                          to_char(po.create_date + '{tz_offset} h'::interval, 'DD/MM/YYYY') as ngay_lap_phieu,
                          to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY') as ngay_hd,
                          pol.product_id                                                   as product_id,
                          pt.categ_id                                                      as categ_id,
                          pol.employee_id                                                  as employee_id,
                          rp.id                                                            as customer_id,
                          rp.ref                                                           as ma_kh,
                          sto.code                                                         as ma_ch,
                          sto.name                                                         as ten_ch,
                          rp.phone                                                         as sdt,
                          rp.name                                                          as ten_kh,
                          pp.barcode                                                       as ma_vach,
                          pol.full_product_name                                            as ten_hang,
                          cate.complete_name                                               as danh_muc_sp,
                          coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US') as don_vi,
                          pt.collection                                                    as bo_suu_tap,
                          greatest(pol.qty, 0)                                             as sl_ban,
                          abs(least(pol.qty, 0))                                           as sl_tra,
                          coalesce(pol.original_price, 0)                                  as gia,
                          emp.name                                                         as nhan_vien,
                          pol.refunded_orderline_id                                        as pol_goc
                   from pos_order po
                            join pos_order_line pol on pol.order_id = po.id
                            join product_product pp on pp.id = pol.product_id
                            join product_template pt on pt.id = pp.product_tmpl_id
                            join uom_uom uom on pt.uom_id = uom.id
                            left join res_partner rp on po.partner_id = rp.id
                            left join pos_session ses on ses.id = po.session_id
                            left join pos_config conf on conf.id = ses.config_id
                            left join store sto on sto.id = conf.store_id
                            left join product_category cate on cate.id = pt.categ_id
                            left join hr_employee emp on emp.id = pol.employee_id
                            {left_join_table}
                   where po.company_id = any (array {allowed_company})
                     and pt.detailed_type <> 'service'
                     and (pt.voucher is false or pt.voucher is null)
                     and (pol.is_promotion is false or pol.is_promotion is null)
                     and (pt.is_product_auto is false or pt.is_product_auto is null)
                     and to_date(to_char(po.date_order + interval '{tz_offset} h', 'YYYY-MM-DD'), 'YYYY-MM-DD') between '{self.from_date}' and '{self.to_date}'
                     and sto.id = any (array {store_ids})
                     and pol.qty <> 0
                     {customer_condition}
                     {order_filter_condition}),
     accounts as (select json_object_agg(cate.id, aa.code) as account_code
                  from product_category cate
                           left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
                           left join account_account aa on concat('account.account,', aa.id) = ir.value_reference
                  where ir.name = 'property_stock_valuation_account_id'
                    and ir.company_id = any (array {allowed_company})
                    and cate.id in (select distinct categ_id from pol_datas)),
     attribute_data as (select json_object_agg(concat(product_id, '~', attrs_code), value) as attrs
                        from (select pp.id                                                                                              as product_id,
                                     pa.attrs_code                                                                                      as attrs_code,
                                     array_to_string(array_agg(coalesce(pav.name::json ->> '{user_lang_code}', pav.name::json ->> 'en_US')), ', ') as value
                              from product_template_attribute_line ptal
                                       left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
                                       left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
                                       left join product_attribute pa on ptal.attribute_id = pa.id
                                       left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
                              where pp.id in (select distinct product_id from pol_datas)
                              group by pp.id, pa.attrs_code) as att),
     ranks as (select json_object_agg(pcr.customer_id, cr.name) as rank
               from partner_card_rank pcr
                        join card_rank cr on cr.id = pcr.card_rank_id
               where pcr.customer_id in (select distinct customer_id from pol_datas)
                 and pcr.brand_id = {self.brand_id.id}),
     promotion_keys as (select '{{
        "point": "Tiêu điểm",
       "card": "Chiết khấu hạng thẻ",
       "product_defective": "Chiết khấu hàng lỗi",
       "handle": "Chiết khấu tay",
       "changed_refund": "Duyệt giá đổi trả hàng"
     }}'::json as keys),
     discounts as (select json_object_agg(pol_id, abs(discount)) as disc
                   from (select pos_order_line_id  as pol_id,
                                sum(money_reduced) as discount
                         from pos_order_line_discount_details
                         where pos_order_line_id in (select distinct pol_id from pol_datas)
                         group by pos_order_line_id) as x),
     x_ctkm as ("""
        query += f"""select pol_id, array_to_string(array_agg(name), ', ') as name
                from (select pul.order_line_id as pol_id,
                             ppr.name          as name
                      from promotion_program ppr
                               join promotion_usage_line pul on ppr.id = pul.program_id
                      where pul.order_line_id in (select distinct pol_id from pol_datas)
                      group by pul.order_line_id, ppr.name
                      union all
                      select s.pos_order_line_id                                                       as pol_id,
                             concat((select keys::json ->> s.type from promotion_keys), ':', s.recipe) as name
                      from pos_order_line_discount_details s
                      where s.pos_order_line_id in (select distinct pol_id from pol_datas)
                        and s.type in (select json_object_keys(keys) from promotion_keys)
                      group by s.pos_order_line_id, concat((select keys::json ->> s.type from promotion_keys), ':', s.recipe)) as xx
                group by pol_id),
     xx_ctkm as (select json_object_agg(pol_id, name) as km from x_ctkm),
     x_ma_the_gg as (select json_object_agg(pol_id, code) as mt_gg
                     from (select pul.order_line_id                         as pol_id,
                                  array_to_string(array_agg(pc.name), ', ') as code
                           from promotion_code pc
                                    join promotion_usage_line pul on pc.id = pul.code_id
                           where pul.order_line_id in (select distinct pol_id from pol_datas)
                           group by pul.order_line_id) as gg),
     x_voucher as (select json_object_agg(po_id, voucher) as voucher
                   from (select pvl.pos_order_id                          as po_id,
                                array_to_string(array_agg(vv.name), ', ') as voucher
                         from voucher_voucher vv
                                  join pos_voucher_line pvl on vv.id = pvl.voucher_id
                         where pvl.pos_order_id in (select distinct po_id from pol_datas)
                         group by pvl.pos_order_id) as vouchers),
     x_don_hang_goc as (select json_object_agg(pol_id, value) as data
                        from (select xx.pol_id                                                               as pol_id,
                                     array [po.name, to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY')] as value
                              from pol_datas xx
                                       join pos_order_line pol on xx.pol_goc = pol.id
                                       join pos_order po on pol.order_id = po.id
                              where pol_goc notnull) as dhg)
select row_number() over (order by po_id)                                        as num,
       ma_ch,
       ten_ch,
       so_hd,
       mo_ta,
       ngay_hd,
       ngay_lap_phieu,
       ma_kh,
       sdt,
       ten_kh,
       ma_vach,
       ten_hang,
       split_part(danh_muc_sp, ' / ', 2)                                         as nhom_hang,
       split_part(danh_muc_sp, ' / ', 3)                                         as dong_hang,
       split_part(danh_muc_sp, ' / ', 4)                                         as ket_cau,
       don_vi,
       (select attrs::json ->> concat(product_id, '~{attr_value.get('nhan_hieu', '')}') from attribute_data) as nhan_hieu,
       (select attrs::json ->> concat(product_id, '~{attr_value.get('size', '')}') from attribute_data) as kich_co,
       (select attrs::json ->> concat(product_id, '~{attr_value.get('mau_sac', '')}') from attribute_data) as mau_sac,
       bo_suu_tap,
       sl_ban,
       sl_tra,
       gia,
       (select disc::json ->> pol_id::text from discounts)::integer              as giam_gia,
       0                                                                         as giam_tren_hd,
       (select rank::json ->> customer_id::text from ranks)                      as hang,
       (select km::json ->> pol_id::text from xx_ctkm)                           as ctkm,
       (select mt_gg::json ->> pol_id::text from x_ma_the_gg)                    as ma_the_gg,
       (select voucher::json ->> po_id::text from x_voucher)                     as voucher,
       (select data::json -> pol_id::text from x_don_hang_goc)                   as don_hang_goc,
       nhan_vien,
       (select account_code::json ->> categ_id::text from accounts)              as ma_loai,
       'Cửa hàng'                                                                as kenh_ban
from pol_datas"""
        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Store = self.env['store'].with_context(report_ctx='report.num20,store')
        store_ids = (Store.search([('brand_id', '=', self.brand_id.id)]).ids or [-1]) if not self.store_ids else self.store_ids.ids
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
        sheet = workbook.add_worksheet('Bảng kê chi tiết hóa đơn bán - đổi - trả')
        sheet.set_row(0, 25)
        sheet.set_row(4, 25)
        sheet.freeze_panes(5, 0)
        sheet.write(0, 0, 'Bảng kê chi tiết hóa đơn bán - đổi - trả', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày: %s đến ngày: %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(TITLES) - 1, 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ma_cn'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ten_cn'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ngay_lap_phieu'), formats.get('center_format'))
            sheet.write(row, 4, value.get('ngay_hd'), formats.get('center_format'))
            sheet.write(row, 5, value.get('so_hd'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ma_kh'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('sdt'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('ten_kh'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('ma_vach'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('ten_hang'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('nhan_hieu'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('kich_co'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('mau_sac'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('don_vi'), formats.get('normal_format'))
            sheet.write(row, 16, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 17, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 18, value.get('bo_suu_tap'), formats.get('normal_format'))
            sheet.write(row, 19, value.get('sl_ban') or 0, formats.get('int_number_format'))
            sheet.write(row, 20, value.get('sl_tra') or 0, formats.get('int_number_format'))
            sheet.write(row, 21, value.get('gia') or 0, formats.get('int_number_format'))
            sheet.write(row, 22, value.get('giam_gia') or 0, formats.get('int_number_format'))
            sheet.write(row, 23, value.get('giam_tren_hd') or 0, formats.get('int_number_format'))
            sl_ban = value.get('sl_ban') or 0
            sl_tra = value.get('sl_tra') or 0
            sheet.write(row, 24, (value.get('gia') or 0) * sl_ban - ((value.get('giam_gia') or 0) if sl_ban else 0), formats.get('int_number_format'))
            sheet.write(row, 25, (value.get('gia') or 0) * sl_tra - ((value.get('giam_gia') or 0) if sl_tra else 0), formats.get('int_number_format'))
            sheet.write(row, 26, value.get('mo_ta'), formats.get('normal_format'))
            sheet.write(row, 27, value.get('hang'), formats.get('normal_format'))
            sheet.write(row, 28, value.get('ctkm'), formats.get('normal_format'))
            sheet.write(row, 29, value.get('ma_the_gg'), formats.get('normal_format'))
            sheet.write(row, 30, value.get('voucher'), formats.get('normal_format'))
            sheet.write(row, 31, value.get('nhan_vien'), formats.get('normal_format'))
            don_hang_goc = value.get('don_hang_goc') or ['', '']
            sheet.write(row, 32, don_hang_goc[0], formats.get('normal_format'))
            sheet.write(row, 33, don_hang_goc[1], formats.get('normal_format'))
            sheet.write(row, 34, value.get('ma_loai'), formats.get('normal_format'))
            sheet.write(row, 35, value.get('kenh_ban'), formats.get('normal_format'))
            row += 1
