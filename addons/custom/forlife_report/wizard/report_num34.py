# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Mã chi nhánh', 'Chi nhánh', 'Ngày', 'Số CT', 'Mã KH', 'Số điện thoại', 'Tên KH', 'Mô tả', 'Mã thẻ GG', 'Voucher', 'Số lượng mua',
    'Số lượng trả', 'Cộng', 'Giảm giá', 'Tổng cộng', 'Giảm trên HĐ', 'Cộng lại', 'Tiền trả lại', 'Tiền thẻ GG', 'Phải thu', 'DT cửa hàng', 'Tiền SHIPCOD',
    'Tiền voucher', 'Người lập', 'Ngày lập', 'Số CT gốc', 'Ngày CT nhập', 'Nhân viên', 'Nhóm khách', 'Mã vận đơn', 'Mã GD gốc', 'Đơn vị VC', 'Kênh bán',
]

TRANSACTION_DETAIL_TITLE = ['STT', 'Mã vạch', 'Tên sản phẩm', 'Đơn vị', 'Số lượng', 'Giá bán', '% Giảm giá', 'Tiền giảm giá', 'Thành tiền']


class ReportNum34(models.TransientModel):
    _name = 'report.num34'
    _inherit = ['report.base', 'export.excel.client']
    _description = 'Danh sách hóa đơn TMĐT'

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
        customer_join = f"""join res_partner rp on so.order_partner_id = rp.id and (rp.ref ilike '%{self.customer}%' or
            rp.name ilike '%{self.customer}%' or rp.phone ilike '%{self.customer}%')""" if self.customer else ''
        so_filter_condition = f"""and so.name ilike '%{self.order_filter}%'""" if self.order_filter else ''
        nhanh_order_condition = f"""and so.nhanh_id ilike '%{self.nhanh_order}%'""" if self.nhanh_order else ''

        query = f"""
with get_data_id_with_condition as (select so.id  as so_id,
                                           sol.id as sol_id
                                    from sale_order so
                                             join sale_order_line sol on so.id = sol.order_id
                                             join stock_location sl on sl.id = so.x_location_id
                                             {customer_join}
                                    where so.source_record = true {so_filter_condition} {nhanh_order_condition}
                                    and so.company_id = any(array{allowed_company})
                                    and sl.warehouse_id = any(array{warehouse_ids})
                                    and {format_date_query("so.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'),
     so_discount_by_product as (select order_line_id as sol_id,
                                       product_id    as product_id,
                                       sum(value)    as discount
                                from sale_order_promotion
                                where order_line_id in (select distinct sol_id from get_data_id_with_condition)
                                  and promotion_type not in ('nhanh_shipping_fee', 'customer_shipping_fee')
                                group by order_line_id, product_id),
     sale_order_lines as (select row_number() over (partition by sol.order_id order by sol.id)     as stt,
                                 sol.order_id                                                      as order_id,
                                 coalesce(so.x_is_return, false)                                   as is_return,
                                 pp.barcode                                                        as ma_vach,
                                 coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')    as ten_sp,
                                 coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')  as don_vi,
                                 sol.product_uom_qty                                               as so_luong,
                                 sol.price_unit                                                    as gia_ban,
                                 coalesce(sdbp.discount, 0)                                        as tien_gg,
                                 case
                                     when (sol.product_uom_qty * sol.price_unit) <> 0
                                         then (coalesce(sdbp.discount, 0) / (sol.product_uom_qty * sol.price_unit) * 100)::float4
                                     else 0 end                                                    as phan_tram_gg,
                                 sol.product_uom_qty * sol.price_unit - coalesce(sdbp.discount, 0) as thanh_tien
                          from sale_order_line sol
                                   join sale_order so on sol.order_id = so.id
                                   left join product_product pp on sol.product_id = pp.id
                                   left join product_template pt on pp.product_tmpl_id = pt.id
                                   left join uom_uom uom on sol.product_uom = uom.id
                                   left join so_discount_by_product sdbp on sdbp.sol_id = sol.id
                              and sdbp.product_id = sol.product_id
                          where sol.id in (select distinct sol_id from get_data_id_with_condition)
                          order by sol.order_id, stt),
     sale_order_lines_qty as (select order_id                                                    as order_id,
                                     sum(case when is_return = false then so_luong else 0 end)   as sl_mua,
                                     sum(case when is_return = true then so_luong else 0 end)    as sl_tra,
                                     sum(case when is_return = false then thanh_tien else 0 end) as cong,
                                     sum(case when is_return = true then thanh_tien else 0 end)  as tien_tra_lai,
                                     sum(tien_gg)                                                as tien_gg
                              from sale_order_lines
                              group by order_id),
     sale_order_lines_fn as (select x.order_id,
                                    array_agg(to_json(x.*)) as detail
                             from sale_order_lines as x
                             group by x.order_id),
     sale_orders as (select row_number() over (order by so.id)                                      as stt,
                            wh.code                                                                 as ma_cn,
                            wh.name                                                                 as ten_cn,
                            to_char(so.date_order + interval '{tz_offset} h', 'DD/MM/YYYY')         as ngay,
                            so.name                                                                 as so_ct,
                            rp.ref                                                                  as ma_kh,
                            rp.phone                                                                as sdt,
                            rp.name                                                                 as ten_kh,
                            ''                                                                      as mo_ta,
                            ''                                                                      as ma_the_gg,
                            so.x_code_voucher                                                       as voucher,
                            coalesce(solq.sl_mua, 0)                                                as sl_mua,
                            coalesce(solq.sl_tra, 0)                                                as sl_tra,
                            coalesce(solq.cong, 0)                                                  as cong,
                            coalesce(solq.tien_gg, 0)                                               as giam_gia,
                            0                                                                       as giam_tren_hd,
                            coalesce(solq.tien_tra_lai, 0)                                          as tien_tra_lai,
                            0                                                                       as tien_the_gg,
                            0                                                                       as phai_thu,
                            0                                                                       as dt_cua_hang,
                            so.nhanh_shipping_fee                                                   as tien_shipcod,
                            so.x_voucher                                                            as tien_voucher,
                            rp2.name                                                                as nguoi_lap,
                            to_char(so.create_date + interval '{tz_offset} h', 'DD/MM/YYYY')        as ngay_lap,
                            so2.name                                                                as so_ct_goc,
                            to_char(so2.date_order + interval '{tz_offset} h', 'DD/MM/YYYY')        as ngay_ct_goc,
                            rp3.name                                                                as nhan_vien,
                            (select array_agg(name)
                             from (select distinct name
                                   from res_partner_retail
                                   where brand_id = 1
                                     and id in (select res_partner_retail_id
                                                from res_partner_res_partner_retail_rel
                                                where res_partner_id = so.order_partner_id)) as xx) as nhom_khach,
                            so.nhanh_id                                                             as ma_van_don,
                            so.nhanh_origin_id                                                      as ma_gd_goc,
                            so.delivery_carrier_id                                                  as don_vi_vc,
                            'TMĐT'                                                                  as kenh_ban,
                            solf.detail                                                             as value_detail
                     from sale_order so
                              left join stock_location sl on so.x_location_id = sl.id
                              left join stock_warehouse wh on sl.warehouse_id = wh.id
                              left join res_partner rp on so.order_partner_id = rp.id
                              join res_users ru on so.create_uid = ru.id
                              left join res_partner rp2 on ru.partner_id = rp2.id
                              join res_users ru2 on so.user_id = ru2.id
                              left join res_partner rp3 on ru2.partner_id = rp3.id
                              left join sale_order so2 on so2.id = so.x_origin
                              left join sale_order_lines_fn solf on solf.order_id = so.id
                              left join sale_order_lines_qty solq on solq.order_id = so.id
                     where so.id in (select distinct so_id from get_data_id_with_condition)
                     order by stt)
select * from sale_orders
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
            'transaction_detail_title': TRANSACTION_DETAIL_TITLE,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Danh sách hóa đơn TMĐT')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Danh sách hóa đơn TMĐT', formats.get('header_format'))
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
            sheet.write(row, 3, value.get('ngay'), formats.get('center_format'))
            sheet.write(row, 4, value.get('so_ct'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('ma_kh'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('sdt'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('ten_kh'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('mo_ta'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('ma_the_gg'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('voucher'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('sl_mua'), formats.get('int_number_format'))
            sheet.write(row, 12, value.get('sl_tra'), formats.get('int_number_format'))
            sheet.write(row, 13, value.get('cong', 0), formats.get('int_number_format'))
            sheet.write(row, 14, value.get('giam_gia', 0), formats.get('int_number_format'))
            sheet.write(row, 15, value.get('cong', 0) - value.get('giam_gia', 0), formats.get('int_number_format'))
            sheet.write(row, 16, value.get('giam_tren_hd', 0), formats.get('int_number_format'))
            sheet.write(row, 17, value.get('cong', 0) - value.get('giam_gia', 0) - value.get('giam_tren_hd', 0), formats.get('int_number_format'))
            sheet.write(row, 18, value.get('tien_tra_lai', 0), formats.get('int_number_format'))
            sheet.write(row, 19, value.get('tien_the_gg', 0), formats.get('int_number_format'))
            sheet.write(row, 20, value.get('phai_thu', 0), formats.get('int_number_format'))
            sheet.write(row, 21, value.get('dt_cua_hang', 0), formats.get('int_number_format'))
            sheet.write(row, 22, value.get('tien_shipcod', 0), formats.get('int_number_format'))
            sheet.write(row, 23, value.get('tien_voucher', 0), formats.get('int_number_format'))
            sheet.write(row, 24, value.get('nguoi_lap'), formats.get('normal_format'))
            sheet.write(row, 25, value.get('ngay_lap'), formats.get('center_format'))
            sheet.write(row, 26, value.get('so_ct_goc'), formats.get('normal_format'))
            sheet.write(row, 27, value.get('ngay_ct_goc'), formats.get('center_format'))
            sheet.write(row, 28, value.get('nhan_vien'), formats.get('normal_format'))
            sheet.write(row, 29, ', '.join(value.get('nhom_khach') or []), formats.get('normal_format'))
            sheet.write(row, 30, value.get('ma_van_don'), formats.get('normal_format'))
            sheet.write(row, 31, value.get('ma_gd_goc'), formats.get('normal_format'))
            sheet.write(row, 32, value.get('don_vi_vc'), formats.get('normal_format'))
            sheet.write(row, 33, value.get('kenh_ban'), formats.get('normal_format'))
            row += 1
