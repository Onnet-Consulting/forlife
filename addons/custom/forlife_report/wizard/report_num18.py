# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Nhà cung cấp', 'Chú ý', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu', 'Sản phẩm', 'Mô tả', 'Loại hàng hóa', 'Số phiếu yêu cầu',
    'Số dòng trên phiếu yêu cầu', 'Mô tả tài sản', 'Số lượng đặt mua', 'Số lượng đã đặt', 'Số lượng đã nhận', 'Đơn vị mua', 'Tỷ lệ quy đổi',
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
    request_user_ids = fields.Many2many('res.users', 'report_num18_request_users_rel', string='Request user')
    receiver_ids = fields.Many2many('hr.employee', 'report_num18_receiver_rel', string='Receiver')
    product_brand_ids = fields.Many2many('product.category', 'report_num18_brand_rel', string='Level 1')
    product_group_ids = fields.Many2many('product.category', 'report_num18_group_rel', string='Level 2')
    product_line_ids = fields.Many2many('product.category', 'report_num18_line_rel', string='Level 3')
    texture_ids = fields.Many2many('product.category', 'report_num18_texture_rel', string='Level 4')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('product_brand_ids')
    def onchange_product_brand(self):
        self.product_group_ids = self.product_group_ids.filtered(lambda f: f.parent_id.id in self.product_brand_ids.ids)

    @api.onchange('product_group_ids')
    def onchange_product_group(self):
        self.product_line_ids = self.product_line_ids.filtered(lambda f: f.parent_id.id in self.product_group_ids.ids)

    @api.onchange('product_line_ids')
    def onchange_product_line(self):
        self.texture_ids = self.texture_ids.filtered(lambda f: f.parent_id.id in self.product_line_ids.ids)

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
            where_condition += f"""\nand ({' or '.join("pr.name ilike '%s'" % i.strip() for i in self.pr_number.split(','))})"""

        if self.request_user_ids:
            where_condition += f"""\nand pr.user_id = any( array{self.request_user_ids.ids})"""

        if self.receiver_ids:
            where_condition += f"""\nand pr.receiver_id = any( array{self.receiver_ids.ids})"""

        Product = self.env['product.product']
        Utility = self.env['res.utility']
        categ_ids = self.texture_ids or self.product_line_ids or self.product_group_ids or self.product_brand_ids
        if categ_ids:
            product_ids = Product.search([('categ_id', 'in', Utility.get_all_category_last_level(categ_ids))]).ids or [-1]
            where_condition += f"""\nand prl.product_id = any( array{product_ids})"""

        sql = f"""
with prepare_data_tb as (
    select 
        '{{"product":"Hàng hóa","service":"Dịch vụ","asset":"Tài sản"}}'::json as product_type,
        '{{"true":"Đóng","false":"Mở"}}'::json as state
),
purchase_request_line_x as (
    select pr.id, 
            prl.id as req_line_id,
            pr.name,
            pr.attention,
            pr.occasion_code_id
    from purchase_request pr
        join purchase_request_line prl on pr.id = prl.request_id
    where pr.company_id = any( array{allowed_company})
  and {format_date_query("pr.request_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
  {where_condition}
),
po_line_qty as (
    select prl.req_line_id                    as req_line_id,
           coalesce(sum(pol.qty_received), 0) as qty
    from purchase_request_line_x prl
             left join purchase_order_line pol on prl.req_line_id = pol.purchase_request_line_id
    group by prl.req_line_id
)
select 
    rp.name                                                                                 as nha_cung_cap,
    polx.attention                                                                          as chu_y,
    split_part(cate.complete_name, ' / ', 2)                                                as nhom_hang,
    split_part(cate.complete_name, ' / ', 3)                                                as dong_hang,
    split_part(cate.complete_name, ' / ', 4)                                                as ket_cau,
    pp.barcode                                                                              as san_pham,
    coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')               as mo_ta,
    (select product_type::json ->> pt.product_type from prepare_data_tb)                    as loai_hh,
    polx.name                                                                               as so_phieu_yc,
    row_number() over (PARTITION BY polx.id ORDER BY polx.id, prl.id)                       as so_dong_tren_phieu_yc,
    prl.asset_description                                                                   as mo_ta_ts,
    coalesce(prl.purchase_quantity, 0)                                                      as sl_dat_mua,
    coalesce(prl.order_quantity, 0)                                                         as sl_da_dat,
    coalesce(plq.qty, 0)                                                                    as sl_da_nhan,
    coalesce(p_uom.name::json ->> '{user_lang_code}', p_uom.name::json ->> 'en_US')         as don_vi_mua,
    prl.exchange_quantity                                                                   as ty_le_quy_doi,
    prl.product_qty                                                                         as sl_ton_kho_quy_doi,
    coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')             as don_vi_tinh,
    coalesce(aaa.name::json ->> '{user_lang_code}', aaa.name::json ->> 'en_US')             as tt_chi_phi,
    fp.name                                                                                 as lenh_sx,
    oc.name                                                                                 as ma_vu_viec,
    to_char(prl.date_planned + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')               as ngay_du_kien,
    (select state::json ->> prl.is_close::text from prepare_data_tb)                        as trang_thai
from purchase_request_line prl
    left join res_partner rp on rp.id = prl.vendor_code
    join product_product pp on pp.id = prl.product_id
    join purchase_request_line_x polx on polx.req_line_id = prl.id
    left join product_template pt on pt.id = pp.product_tmpl_id
    left join uom_uom uom on uom.id = pt.uom_id
    left join uom_uom p_uom on p_uom.id = prl.purchase_uom
    left join account_analytic_account aaa on aaa.id = prl.account_analytic_id
    left join forlife_production fp on fp.id = prl.production_id
    left join occasion_code oc on oc.id = polx.occasion_code_id
    left join po_line_qty plq on plq.req_line_id = prl.id
    left join product_category cate on pt.categ_id = cate.id
  order by polx.id, prl.id
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
            sheet.write(row, 1, value.get('chu_y'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('san_pham'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('mo_ta'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('loai_hh'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('so_phieu_yc'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('so_dong_tren_phieu_yc'), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('mo_ta_ts'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('sl_dat_mua'), formats.get('int_number_format'))
            sheet.write(row, 12, value.get('sl_da_dat'), formats.get('int_number_format'))
            sheet.write(row, 13, value.get('sl_da_nhan'), formats.get('int_number_format'))
            sheet.write(row, 14, value.get('don_vi_mua'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('ty_le_quy_doi'), formats.get('float_number_format'))
            sheet.write(row, 16, value.get('sl_ton_kho_quy_doi'), formats.get('float_number_format'))
            sheet.write(row, 17, value.get('don_vi_tinh'), formats.get('normal_format'))
            sheet.write(row, 18, value.get('tt_chi_phi'), formats.get('normal_format'))
            sheet.write(row, 19, value.get('lenh_sx'), formats.get('normal_format'))
            sheet.write(row, 20, value.get('ma_vu_viec'), formats.get('normal_format'))
            sheet.write(row, 21, value.get('ngay_du_kien'), formats.get('center_format'))
            sheet.write(row, 22, value.get('trang_thai'), formats.get('normal_format'))
            row += 1
