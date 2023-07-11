# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Nhà cung cấp', 'Ghi chú', 'Sản phẩm', 'Mô tả', 'Loại hàng hóa', 'Số phiếu yêu cầu', 'Số dòng trên phiếu yêu cầu',
    'Mô tả tài sản', 'Số lượng đặt mua', 'Số lượng đã đặt', 'Số lượng còn lại', 'Đơn vị mua', 'Tỷ lệ quy đổi',
    'Số lượng tồn kho quy đổi', 'Đơn vị tính', 'Trung tâm chi phí', 'Lệnh sản xuất', 'Mã vụ việc', 'Ngày dự kiến nhận hàng', 'Trạng thái'
]


class ReportNum18(models.TransientModel):
    _name = 'report.num18'
    _inherit = 'report.base'
    _description = 'Purchase Request Detail Report'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    pr_number = fields.Text('PR number')
    state = fields.Selection([('open', _('Open')), ('close', _('Close')), ('all', _('All'))], string='State', default='all', required=True)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self, allowed_company):
        self.ensure_one()
        tz_offset = self.tz_offset
        user_lang_code = self.env.user.lang

        where_condition = ''
        state_condition = {
            'open': 'and prl.is_close = false\n',
            'close': 'and prl.is_close = true\n',
            'all': '',
        }
        where_condition += state_condition.get(self.state, '')

        if self.pr_number:
            where_condition += f"""and ({' or '.join("pr.name ilike '%s'" % i.strip() for i in self.pr_number.split(','))})"""

        sql = f"""
with prepare_data_tb as (
    select 
        '{{"product":"Hàng hóa","service":"Dịch vụ","asset":"Tài sản"}}'::json as product_type,
        '{{"true":"Đóng","false":"Mở"}}'::json as state
)
select 
    rp.name                                                                                 as nha_cung_cap,
    ''                                                                                      as ghi_chu,
    pp.barcode                                                                              as san_pham,
    coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US') as mo_ta,
    (select product_type::json ->> pt.product_type from prepare_data_tb)                    as loai_hh,
    pr.name                                                                                 as so_phieu_yc,
    row_number() over (PARTITION BY pr.id ORDER BY pr.id, prl.id)                           as so_dong_tren_phieu_yc,
    prl.asset_description                                                                   as mo_ta_ts,
    prl.purchase_quantity                                                                   as sl_dat_mua,
    prl.order_quantity                                                                      as sl_da_dat,
    prl.purchase_quantity - prl.order_quantity                                              as sl_con_lai,
    coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')               as don_vi_mua,
    prl.exchange_quantity                                                                   as ty_le_quy_doi,
    prl.product_qty                                                                         as sl_ton_kho_quy_doi,
    coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')               as don_vi_tinh,
    coalesce(aaa.name::json ->> '{user_lang_code}', aaa.name::json ->> 'en_US')               as tt_chi_phi,
    fp.name                                                                                 as lenh_sx,
    oc.name                                                                                 as ma_vu_viec,
    to_char(prl.date_planned + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')               as ngay_du_kien,
    (select state::json ->> prl.is_close::text from prepare_data_tb)                         as trang_thai
from purchase_request_line prl
    left join res_partner rp on rp.id = prl.vendor_code
    join product_product pp on pp.id = prl.product_id
    join purchase_request pr on pr.id = prl.request_id
    left join product_template pt on pt.id = pp.product_tmpl_id
    left join uom_uom uom on uom.id = pt.uom_id
    left join account_analytic_account aaa on aaa.id = prl.account_analytic_id
    left join forlife_production fp on fp.id = prl.production_id
    left join occasion_code oc on oc.id = pr.occasion_code_id
where pr.company_id = any( array{allowed_company})
  and {format_date_query("pr.request_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
  {where_condition}
  order by pr.id, prl.id
"""
        return sql

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
        state = {
            'open': 'Mở',
            'close': 'Đóng',
            'all': 'Tất cả',
        }
        sheet = workbook.add_worksheet('Báo cáo chi tiết PR')
        sheet.set_row(0, 25)
        sheet.set_column(0, len(TITLES) - 1, 18)
        sheet.write(0, 0, 'Báo cáo chi tiết PR', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày: %s' % self.from_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(3, 0, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 3, 'Số PR: %s' % (self.pr_number or ''), formats.get('italic_format'))
        sheet.write(3, 3, 'Trạng thái: %s' % state.get(self.state, ''), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(5, idx, title, formats.get('title_format'))
        row = 6
        for value in data['data']:
            sheet.write(row, 0, value.get('nha_cung_cap'), formats.get('normal_format'))
            sheet.write(row, 1, value.get('ghi_chu'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('san_pham'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('mo_ta'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('loai_hh'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('so_phieu_yc'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('so_dong_tren_phieu_yc'), formats.get('int_number_format'))
            sheet.write(row, 7, value.get('mo_ta_ts'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('sl_dat_mua'), formats.get('int_number_format'))
            sheet.write(row, 9, value.get('sl_da_dat'), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('sl_con_lai'), formats.get('int_number_format'))
            sheet.write(row, 11, value.get('don_vi_mua'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('ty_le_quy_doi'), formats.get('float_number_format'))
            sheet.write(row, 13, value.get('sl_ton_kho_quy_doi'), formats.get('float_number_format'))
            sheet.write(row, 14, value.get('don_vi_tinh'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('tt_chi_phi'), formats.get('normal_format'))
            sheet.write(row, 16, value.get('lenh_sx'), formats.get('normal_format'))
            sheet.write(row, 17, value.get('ma_vu_viec'), formats.get('normal_format'))
            sheet.write(row, 18, value.get('ngay_du_kien'), formats.get('center_format'))
            sheet.write(row, 19, value.get('trang_thai'), formats.get('normal_format'))
            row += 1
