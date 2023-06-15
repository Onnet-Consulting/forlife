# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Mã chi nhánh', 'Chi nhánh', 'Ngày', 'Số CT', 'Mã KH', 'SĐT', 'Tên KH', 'Mô tả', 'Mã thẻ GG', 'Voucher', 'Số lượng mua',
    'Số lượng trả', 'Cộng', 'Giảm giá', 'Tổng cộng', 'Giảm trên HĐ', 'Cộng lại', 'Tiền đặt cọc', 'Tiền trả lại', 'Tiền tích lũy',
    'Tích lũy HĐ', 'Trừ tích lũy', 'Tiền thẻ GG', 'Phải thu', 'DT cửa hàng', 'Tiền mặt', 'Tiền thẻ', 'Tiền VNPay', 'Tiền SHIPCOD', 'Tiền voucher',
    'Người lập', 'Ngày lập', 'Người sửa', 'Ngày sửa', 'Số CT nhập', 'Ngày CT nhập', 'Nhân viên', 'Nhóm khách', 'Mã Vận đơn/Mã GD gốc', 'Kênh bán',
]


class ReportNum17(models.TransientModel):
    _name = 'report.num17'
    _inherit = 'report.base'
    _description = 'Invoice sales and refund list'

    lock_date = fields.Date('Lock date')
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_id = fields.Many2one('store', string='Store')
    type = fields.Selection([('store', _('Store')), ('ecommerce', _('Ecommerce'))], string='Sale Type', required=True, default='store')
    customer = fields.Char('Customer-info')
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
        store_key = 'format' if self.brand_id.code == 'FMT' else 'forlife'
        customer_join = f"""join res_partner rp on rp.id = po.partner_id and (rp.ref ilike '%{self.customer}%' or
            rp.name ilike '%{self.customer}%' or rp.phone ilike '%{self.customer}%')""" if self.customer else ''
        order_filter_condition = f"""and (po.pos_reference ilike '%{self.order_filter}%'
             or po.id in (select order_id from pos_order_line where product_id in (
                select id from product_product where default_code ilike '%{self.order_filter}%'))
             or po.id in (select order_id from promotion_usage_line where code_id in(
                select id from promotion_code where name ilike '%{self.order_filter}%')))""" if self.order_filter else ''

        query = f"""
with po_datas as (
    select po.id as id
    from pos_order po
    {customer_join}
    where po.brand_id = {self.brand_id.id} and po.company_id = any( array{allowed_company})
    and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
    and po.session_id in (select id from pos_session where config_id in (select id from pos_config where store_id = any(array{store_ids})))
    {order_filter_condition}
),
ma_the_gg_x as (
    select po_id, array_agg(code) as codes
    from (select DISTINCT pul.order_id as po_id, pro_code.name as code
        from promotion_usage_line pul
            join promotion_code pro_code on pro_code.id = pul.code_id
        where pul.order_id in (select id from po_datas)
    ) as xx group by po_id
),
voucher_x as (
    select po_id, array_agg(voucher) as vouchers
    from (select DISTINCT pvl.pos_order_id as po_id, vv.name as voucher
        from pos_voucher_line pvl
            join voucher_voucher vv on vv.id = pvl.voucher_id
        where pvl.pos_order_id in (select id from po_datas)
    ) as xx group by po_id
),
so_luong_x as (
    select 
        po.id                                                       as po_id,
        sum(greatest(pol.qty, 0))::float                            as sl_mua,
        - sum(least(pol.qty, 0))                                    as sl_tra,
        sum(greatest(pol.qty, 0) * pol.original_price)::float       as cong,
        sum(case when disc.type = 'point' then disc.recipe * 1000
                when disc.type = 'card' then disc.recipe
                when disc.type = 'ctkm' then disc.discounted_amount
                else 0
            end)::float                                             as giam_gia,
        sum(- least(pol.qty, 0) * pol.original_price)::float        as tien_tra_lai,
        sum(pul.discount_amount * pol.qty)::float                   as tien_the_gg
    from pos_order po
        join pos_order_line pol on pol.order_id = po.id
        left join pos_order_line_discount_details disc on disc.pos_order_line_id = pol.id
        left join promotion_usage_line pul on pul.order_line_id = pol.id and pul.code_id notnull
    where po.id in (select id from po_datas)
    group by po_id
)
select
    row_number() over (order by po.id)                                  as num,
    sto.code                                                            as ma_cn,
    sto.name                                                            as ten_cn,
    to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY')    as ngay,
    po.pos_reference                                                    as so_ct,
    rp.ref                                                              as ma_kh,
    rp.phone                                                            as sdt,
    rp.name                                                             as ten_kh,
    ''                                                                  as mo_ta,
    gg_x.codes                                                          as ma_the_gg,
    v_x.vouchers                                                        as voucher,
    sl_x.sl_mua                                                         as sl_mua,
    sl_x.sl_tra                                                         as sl_tra,
    sl_x.cong                                                           as cong,
    sl_x.giam_gia                                                       as giam_gia,
    coalesce(sl_x.cong - sl_x.giam_gia, 0)                              as tong_cong,
    0                                                                   as giam_tren_hd,
    0                                                                   as tien_dat_coc,
    coalesce(sl_x.tien_tra_lai, 0)                                      as tien_tra_lai,
    (select coalesce(sum(points_store), 0) * 1000 from (
        select points_store from partner_history_point
        where store = '{store_key}'
         and date_order < po.date_order and partner_id = po.partner_id
    ) as xx)                                                            as tien_tich_luy,
    coalesce((select sum(points_fl_order) from partner_history_point
     where pos_order_id = po.id), 0) * 1000                             as tich_luy_hd,
    (select coalesce(sum(points_used), 0) * 1000 from (
        select points_used from partner_history_point
        where store = '{store_key}'
         and date_order < po.date_order and partner_id = po.partner_id
    ) as xx)                                                            as tru_tich_luy,
    coalesce(sl_x.tien_the_gg, 0)                                       as tien_the_gg,
    coalesce(po.amount_total, 0)::float                                 as phai_thu,
    coalesce((select sum(amount) from pos_payment
            where pos_order_id = po.id and payment_method_id in (
                select id from pos_payment_method
                where (is_voucher = false or is_voucher is null)
                    and company_id = any( array{allowed_company}) and journal_id in (
                    select id from account_journal where type = 'cash')
                )
        ), 0)                                                                   as tien_mat,
    coalesce((select sum(amount) from pos_payment
            where pos_order_id = po.id and payment_method_id in (
                select id from pos_payment_method
                where (is_voucher = false or is_voucher is null)
                    and company_id = any( array{allowed_company}) and journal_id in (
                    select id from account_journal where type = 'bank')
                )
        ), 0)                                                                   as tien_the,
    0                                                                           as tien_vnpay,
    0                                                                           as tien_shipcod,
    coalesce((select sum(amount) from pos_payment
            where pos_order_id = po.id and payment_method_id in (
                select id from pos_payment_method
                where is_voucher = true and company_id = any( array{allowed_company})
                )
        ), 0)                                                                   as tien_voucher,
    nl.name                                                                     as nguoi_lap,
    to_char(po.create_date + '{tz_offset} h'::interval, 'DD/MM/YYYY')           as ngay_lap,
    ''                                                                          as nguoi_sua,
    ''                                                                          as ngay_sua,
    (select array_agg(pos_reference)
    from pos_order where id in (
        select order_id from pos_order_line where id in (
            select refunded_orderline_id
            from pos_order_line
            where refunded_orderline_id notnull and order_id = po.id)
        ))                                                                      as so_ct_nhap,
    (select array_agg(to_char(date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY'))
    from pos_order where id in (
        select order_id from pos_order_line where id in (
            select refunded_orderline_id
            from pos_order_line
            where refunded_orderline_id notnull and order_id = po.id)
        ))                                                                      as ngay_ct_nhap,
    (select array_agg(name) from (
        select distinct name from hr_employee where id in (
            select employee_id from pos_order_line where order_id = po.id
            )
    ) as xx)                                                                    as nhan_vien,
    (select array_agg(name) from (
        select distinct name from res_partner_retail
        where brand_id = {self.brand_id.id} and id in (
            select res_partner_retail_id from res_partner_res_partner_retail_rel
            where res_partner_id = po.partner_id
            )
     ) as xx)                                                                   as nhom_khach,
    ''                                                                          as ma_van_don,
    'Cửa hàng'                                                                  as kenh_ban
from pos_order po
    left join res_partner rp on po.partner_id = rp.id
    left join res_partner nl on po.user_id = nl.id
    left join pos_session ses on ses.id = po.session_id
    left join pos_config conf on conf.id = ses.config_id
    left join store sto on sto.id = conf.store_id
    left join ma_the_gg_x gg_x on gg_x.po_id = po.id
    left join voucher_x v_x on v_x.po_id = po.id
    left join so_luong_x sl_x on sl_x.po_id = po.id
where po.id in (select id from po_datas)
order by num
"""
        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        store_ids = (self.env['store'].search([('brand_id', '=', self.brand_id.id)]).ids or [-1]) if not self.store_id else self.store_id.ids
        query = self._get_query(store_ids, allowed_company)
        data = self.execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Danh sách hóa đơn bán - đổi - trả')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Danh sách hóa đơn bán - đổi - trả', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày: %s đến ngày: %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ma_cn'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ten_cn'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ngay'), formats.get('center_format'))
            sheet.write(row, 4, value.get('so_ct'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('ma_kh'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('sdt'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('ten_kh'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('mo_ta'), formats.get('normal_format'))
            sheet.write(row, 9, ', '.join(value.get('ma_the_gg') or []), formats.get('normal_format'))
            sheet.write(row, 10, ', '.join(value.get('voucher') or []), formats.get('normal_format'))
            sheet.write(row, 11, value.get('sl_mua'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('sl_tra'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('cong', 0), formats.get('int_number_format'))
            sheet.write(row, 14, value.get('giam_gia', 0), formats.get('int_number_format'))
            sheet.write(row, 15, value.get('tong_cong', 0), formats.get('int_number_format'))
            sheet.write(row, 16, value.get('giam_tren_hd', 0), formats.get('int_number_format'))
            sheet.write(row, 17, value.get('tong_cong', 0) - value.get('giam_tren_hd', 0), formats.get('int_number_format'))
            sheet.write(row, 18, value.get('tien_dat_coc', 0), formats.get('normal_format'))
            sheet.write(row, 19, value.get('tien_tra_lai', 0), formats.get('int_number_format'))
            sheet.write(row, 20, value.get('tien_tich_luy', 0), formats.get('int_number_format'))
            sheet.write(row, 21, value.get('tich_luy_hd', 0), formats.get('int_number_format'))
            sheet.write(row, 22, value.get('tru_tich_luy', 0), formats.get('int_number_format'))
            sheet.write(row, 23, value.get('tien_the_gg', 0), formats.get('int_number_format'))
            sheet.write(row, 24, value.get('phai_thu', 0), formats.get('int_number_format'))
            sheet.write(row, 25, value.get('phai_thu', 0) - (value.get('tien_voucher', 0) / 2), formats.get('int_number_format'))
            sheet.write(row, 26, value.get('tien_mat', 0), formats.get('int_number_format'))
            sheet.write(row, 27, value.get('tien_the', 0), formats.get('int_number_format'))
            sheet.write(row, 28, value.get('tien_vnpay', 0), formats.get('int_number_format'))
            sheet.write(row, 29, value.get('tien_shipcod', 0), formats.get('int_number_format'))
            sheet.write(row, 30, value.get('tien_voucher', 0), formats.get('int_number_format'))
            sheet.write(row, 31, value.get('nguoi_lap'), formats.get('normal_format'))
            sheet.write(row, 32, value.get('ngay_lap'), formats.get('center_format'))
            sheet.write(row, 33, value.get('nguoi_sua'), formats.get('normal_format'))
            sheet.write(row, 34, value.get('ngay_sua'), formats.get('center_format'))
            sheet.write(row, 35, ', '.join(value.get('so_ct_nhap') or []), formats.get('normal_format'))
            sheet.write(row, 36, ', '.join(value.get('ngay_ct_nhap') or []), formats.get('normal_format'))
            sheet.write(row, 37, ', '.join(value.get('nhan_vien') or []), formats.get('normal_format'))
            sheet.write(row, 38, ', '.join(value.get('nhom_khach') or []), formats.get('normal_format'))
            sheet.write(row, 39, value.get('ma_van_don'), formats.get('normal_format'))
            sheet.write(row, 40, value.get('kenh_ban'), formats.get('normal_format'))
            row += 1
