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
    _description = 'Report sales and refund'

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

    def _get_query(self, store_ids):
        self.ensure_one()
        tz_offset = self.tz_offset
        store_key = 'format' if self.brand_id.code == 'FMT' else 'forlife'
        customer_condition = f"and (rp.ref ilike '%{self.customer}%' or rp.phone ilike '%{self.customer}%')" if self.customer else ''
        order_filter_condition = f"""and (po.pos_reference ilike '%{self.order_filter}%'
             or po.id in (select order_id from pos_order_line where product_id in (
                select id from product_product where default_code ilike '%{self.order_filter}%'))
             or po.id in (select order_id from promotion_usage_line where code_id in(
                select id from promotion_code where name ilike '%{self.order_filter}%')))""" if self.order_filter else ''
        query = f"""
select
    coalesce((select array[code, name] from store where id in (
        select store_id from pos_config where id in (
            select config_id from pos_session where id = po.session_id
            ) 
        ) limit 1
    ), array['', ''] )                                                          as chi_nhanh,
    to_char(po.date_order, 'DD/MM/YYYY')                                        as ngay,
    po.pos_reference                                                            as so_ct,
    rp.ref                                                                      as ma_kh,
    rp.phone                                                                    as sdt,
    rp.name                                                                     as ten_kh,
    ''                                                                          as mo_ta,
    (select array_agg(name) from (
        select distinct name from promotion_code where id in (
            select code_id from promotion_usage_line where order_id = po.id
            )) as xx)                                                           as ma_the_gg,
    (select array_agg(name) from (
        select distinct name from voucher_voucher where id in (
            select voucher_id from pos_voucher_line where pos_order_id = po.id
            )) as xx)                                                           as voucher,
    (select coalesce(sum(qty), 0) from pos_order_line
     where order_id = po.id and qty > 0)                                        as sl_mua,
    (select coalesce(sum(qty), 0) from pos_order_line
     where order_id = po.id and qty < 0)                                        as sl_tra,
    (select coalesce(sum(qty * price_unit), 0)
     from pos_order_line where order_id = po.id)                                as cong,
    (select coalesce(sum(money_reduced), 0) from (
        select case when type = 'card' then - recipe
                    when type = 'point' then recipe * 1000
                    else 0 end as money_reduced
        from pos_order_line_discount_details
        where pos_order_line_id in (
            select id from pos_order_line where order_id = po.id
       )) as xx)                                                                as giam_gia,
    0 as giam_tren_hd,
    '' as tien_dat_coc,
    (select coalesce(sum(qty * price_unit), 0) from pos_order_line
     where order_id = po.id and qty < 0)                                        as tien_tra_lai,
    (select coalesce(sum(points_store), 0) * 1000 from (
        select points_store from partner_history_point
        where store = '{store_key}' and date_order < po.date_order
    ) as xx)                                                                    as tien_tich_luy,
    coalesce((select points_fl_order from partner_history_point
     where pos_order_id = po.id), 0) * 1000                                     as tich_luy_hd,
    coalesce((select points_fl_order from partner_history_point
     where pos_order_id = po.id), 0) * 1000                                     as tru_tich_luy,
    coalesce((select sum(pul.discount_amount * (select coalesce(qty, 0)
                    from pos_order_line where id = pul.order_line_id))
              from promotion_usage_line pul
        where pul.order_id = po.id and pul.code_id notnull), 0)                 as tien_the_gg,
    coalesce(po.amount_total, 0)                                                as phai_thu,
    coalesce((select sum(amount) from pos_payment
            where pos_order_id = po.id and payment_method_id in (
                select id from pos_payment_method
                where (is_voucher = false or is_voucher is null)
                    and company_id = {self.company_id.id} and journal_id in (
                    select id from account_journal where type = 'cash')
                )
        ), 0)                                                                   as tien_mat,
    coalesce((select sum(amount) from pos_payment
            where pos_order_id = po.id and payment_method_id in (
                select id from pos_payment_method
                where (is_voucher = false or is_voucher is null)
                    and company_id = {self.company_id.id} and journal_id in (
                    select id from account_journal where type = 'bank')
                )
        ), 0)                                                                   as tien_the,
    0                                                                           as tien_vnpay,
    0                                                                           as tien_shipcod,
    coalesce((select sum(amount) from pos_payment
            where pos_order_id = po.id and payment_method_id in (
                select id from pos_payment_method
                where is_voucher = true and company_id = {self.company_id.id}
                )
        ), 0)                                                                   as tien_voucher,
    (select name from res_partner where id = (
        select partner_id from res_users where id = po.user_id))                as nguoi_lap,
    to_char(po.create_date, 'DD/MM/YYYY')                                       as ngay_lap,
    '' as nguoi_sua,
    '' as ngay_sua,
    (select array_agg(pos_reference)
    from pos_order where id in (
        select order_id from pos_order_line where id in (
            select refunded_orderline_id
            from pos_order_line
            where refunded_orderline_id notnull and order_id = po.id)
        ))                                                                      as so_ct_nhap,
    (select array_agg(to_char(date_order, 'DD/MM/YYYY'))
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
        where brand_id = 2 and id in (
            select res_partner_retail_id from res_partner_res_partner_retail_rel
            where res_partner_id = po.partner_id
            )
     ) as xx)                                                                   as nhom_khach,
    '' as ma_van_don,
    'Cửa hàng'                                                                  as kenh_ban
from pos_order po
    left join res_partner rp on po.partner_id = rp.id
where po.brand_id = {self.brand_id.id} and po.company_id = {self.company_id.id}
    and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
    and po.session_id in (select id from pos_session where config_id in (select id from pos_config where store_id = any(array{store_ids})))
    {customer_condition}
    {order_filter_condition}
"""
        return query

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        store_ids = (self.env['store'].search([('brand_id', '=', self.brand_id.id)]).ids or [-1]) if not self.store_id else self.store_id.ids
        query = self._get_query(store_ids)
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values
