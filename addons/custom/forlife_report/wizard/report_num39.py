# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Ngày nhập kho', 'Số CT', 'Kho nhập', 'Mã đối tượng', 'Tên đối tượng', 'Thương hiệu', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu', 'Mã vạch',
    'Mã hàng', 'Tên hàng', 'Đơn vị tính', 'Số lượng nhập kho', 'Giá trị nhập kho', 'Chi phí trước thuế', 'Thuế nhập khẩu', 'Thuế tiêu thụ đặc biệt',
    'Chi phí sau thuế', 'Chi phí NPL', 'Chi phí nhân công', 'Tổng tiền', 'Tài khoản kho hạch toán', 'Diễn giải', 'Số PO tham chiếu'
]


class ReportNum39(models.TransientModel):
    _name = 'report.num39'
    _inherit = ['report.base', 'report.category.type']
    _description = 'Báo cáo chi tiết nhập hàng theo phiếu kho'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    product_ids = fields.Many2many('product.product', 'report_num39_product_rel', string='Products')
    product_group_ids = fields.Many2many('product.category', 'report_num39_group_rel', string='Level 2')
    product_line_ids = fields.Many2many('product.category', 'report_num39_line_rel', string='Level 3')
    texture_ids = fields.Many2many('product.category', 'report_num39_texture_rel', string='Level 4')
    warehouse_ids = fields.Many2many('stock.warehouse', 'report_num39_warehouse_rel', string='Warehouse')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('product_brand_id')
    def onchange_product_brand(self):
        self.product_group_ids = self.product_group_ids.filtered(lambda f: f.parent_id.id in self.product_brand_id.ids)

    @api.onchange('product_group_ids')
    def onchange_product_group(self):
        self.product_line_ids = self.product_line_ids.filtered(lambda f: f.parent_id.id in self.product_group_ids.ids)

    @api.onchange('product_line_ids')
    def onchange_product_line(self):
        self.texture_ids = self.texture_ids.filtered(lambda f: f.parent_id.id in self.product_line_ids.ids)

    def _get_query(self, product_ids, warehouse_ids, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset

        query_final = f"""
with account_by_categ_id as (
    select 
        cate.id as cate_id,
        aa.code as account_code
    from product_category cate
        left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
        left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
    where  ir.name='property_stock_valuation_account_id' and ir.company_id = any( array{allowed_company})
    order by cate.id 
),
stock_moves as (
    select sm.id                              as move_id,
           coalesce(pol.before_tax, 0)                     as cp_truoc_thue,
           coalesce(pol.tax_amount, 0)                     as thue_nk,
           coalesce(pol.special_consumption_tax_amount, 0) as thue_ttdb,
           coalesce(pol.after_tax, 0)                      as cp_sau_thue,
           coalesce(pol.material_cost, 0)                  as cp_npl,
           coalesce(pol.labor_cost, 0)                     as cp_nc,
           coalesce(sum(svl.quantity), 0)                  as qty_in,
           coalesce(sum(svl.value), 0)                     as value
    from stock_move sm
             join purchase_order_line pol on sm.purchase_line_id = pol.id
             left join stock_location sl on sm.location_dest_id = sl.id
             left join stock_valuation_layer svl on svl.stock_move_id = sm.id
    where sm.state = 'done'
      and sm.company_id = any (array{allowed_company})
      and {format_date_query("sm.date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
      and sm.product_id = any (array {product_ids})
      and sl.warehouse_id = any (array {warehouse_ids})
    group by move_id, cp_truoc_thue, thue_nk, thue_ttdb, cp_sau_thue, cp_npl, cp_nc
)
select row_number() over ()                                                         as stt,
       to_char(sm.date + interval '{tz_offset} h', 'DD/MM/YYYY')                    as ngay,
       case when sp.transfer_id notnull then sp.origin else sp.name end             as so_ct,
       coalesce(wh.name, sl.name)                                                   as kho_nhap,
       rp.ref                                                                       as ma_doi_tuong,
       rp.name                                                                      as ten_doi_tuong,
       split_part(cate.complete_name, ' / ', 1)                                     as thuong_hieu,
       split_part(cate.complete_name, ' / ', 2)                                     as nhom_hang,
       split_part(cate.complete_name, ' / ', 3)                                     as dong_hang,
       split_part(cate.complete_name, ' / ', 4)                                     as ket_cau,
       pp.barcode                                                                   as ma_vach,
       pt.sku_code                                                                  as ma_hang,
       coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')    as ten_hang,
       coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')  as dv_tinh,
       coalesce(sms.qty_in, 0)                                                      as sl_nhap,
       coalesce(sms.value, 0)                                                       as gt_nhap,
       sms.cp_truoc_thue                                                            as cp_truoc_thue,
       sms.thue_nk                                                                  as thue_nhap_khau,
       sms.thue_ttdb                                                                as thue_tieu_thu_db,
       sms.cp_sau_thue                                                              as cp_sau_thue,
       sms.cp_npl                                                                   as cp_npl,
       sms.cp_nc                                                                    as cp_nc,
       sms.cp_truoc_thue + sms.thue_nk + sms.thue_ttdb + sms.cp_sau_thue + sms.cp_npl + sms.cp_nc
                                                                                    as tong,
       acc.account_code                                                             as tk_hach_toan,
       sm.name                                                                      as dien_giai,
       sm.origin                                                                    as so_po_tham_chieu
from stock_move sm
    join stock_moves sms on sms.move_id = sm.id
    left join stock_picking sp on sm.picking_id = sp.id
    left join res_partner rp on sp.partner_id = rp.id
    left join stock_location sl on sm.location_dest_id = sl.id
    left join stock_warehouse wh on wh.id = sl.warehouse_id
    left join product_product pp on pp.id = sm.product_id
    left join product_template pt on pt.id = pp.product_tmpl_id
    left join uom_uom uom on uom.id = sm.product_uom
    join product_category cate on cate.id = pt.categ_id
    left join account_by_categ_id acc on acc.cate_id = cate.id
    join purchase_order_line pol on pol.id = sm.purchase_line_id and sm.purchase_line_id notnull
order by stt
"""
        return query_final

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Product = self.env['product.product'].with_context(report_ctx='report.num39,product.product')
        Warehouse = self.env['stock.warehouse'].with_context(report_ctx='report.num39,stock.warehouse')
        Utility = self.env['res.utility']
        categ_ids = self.texture_ids or self.product_line_ids or self.product_group_ids or self.product_brand_id
        if self.product_ids:
            product_ids = self.product_ids.ids
        elif categ_ids:
            product_ids = Product.search([('categ_id', 'in', Utility.get_all_category_last_level(categ_ids))]).ids or [-1]
        else:
            product_ids = [-1]
        warehouse_ids = self.warehouse_ids.ids if self.warehouse_ids else (Warehouse.search([('company_id', 'in', allowed_company)]).ids or [-1])
        query = self._get_query(product_ids, warehouse_ids, allowed_company)
        data = Utility.execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo chi tiết nhập hàng theo phiếu kho')
        sheet.set_row(0, 30)
        sheet.set_row(4, 30)
        sheet.write(0, 0, 'Báo cáo chi tiết nhập hàng theo phiếu kho', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày %s' % self.from_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 2, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(TITLES) - 1, 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ngay'), formats.get('center_format'))
            sheet.write(row, 2, value.get('so_ct'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('kho_nhap'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ma_doi_tuong'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('ten_doi_tuong'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('thuong_hieu'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('ma_vach'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('ma_hang'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('ten_hang'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('dv_tinh'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('sl_nhap'), formats.get('int_number_format'))
            sheet.write(row, 15, value.get('gt_nhap'), formats.get('int_number_format'))
            sheet.write(row, 16, value.get('cp_truoc_thue'), formats.get('int_number_format'))
            sheet.write(row, 17, value.get('thue_nhap_khau'), formats.get('int_number_format'))
            sheet.write(row, 18, value.get('thue_tieu_thu_db'), formats.get('int_number_format'))
            sheet.write(row, 19, value.get('cp_sau_thue'), formats.get('int_number_format'))
            sheet.write(row, 20, value.get('cp_npl'), formats.get('int_number_format'))
            sheet.write(row, 21, value.get('cp_nc'), formats.get('int_number_format'))
            sheet.write(row, 22, value.get('tong'), formats.get('int_number_format'))
            sheet.write(row, 23, value.get('tk_hach_toan'), formats.get('normal_format'))
            sheet.write(row, 24, value.get('dien_giai'), formats.get('normal_format'))
            sheet.write(row, 25, value.get('so_po_tham_chieu'), formats.get('normal_format'))
            row += 1
