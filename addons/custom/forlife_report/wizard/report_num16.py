# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Ngày', 'Số CT', 'Kho', 'Số CT2', 'Kho2', 'Mã khách', 'Tên khách', 'Đối tượng', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu',
    'Mã vạch', 'Mã hàng', 'Tên hàng', 'Màu sắc', 'Kích cỡ', 'Năm sản xuất', 'Bộ sưu tập', 'Xuất xứ', 'Subclass 1', 'Subclass 2',
    'Subclass 3', 'Subclass 4', 'Subclass 5', 'Đơn vị tính', 'Nhập kho', 'Xuất kho', 'Đơn giá', 'Mã loại', 'Ngày tờ khai', 'Diễn giải',
]


class ReportNum16(models.TransientModel):
    _name = 'report.num16'
    _inherit = ['report.base', 'report.category.type']
    _description = 'Report stock move'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    product_ids = fields.Many2many('product.product', 'report_num16_product_rel', string='Products')
    product_group_ids = fields.Many2many('product.category', 'report_num16_group_rel', string='Level 2')
    product_line_ids = fields.Many2many('product.category', 'report_num16_line_rel', string='Level 3')
    texture_ids = fields.Many2many('product.category', 'report_num16_texture_rel', string='Level 4')
    warehouse_ids = fields.Many2many('stock.warehouse', 'report_num16_warehouse_rel', string='Warehouse')
    move_type = fields.Selection([('all', _('All')), ('in', _('In')), ('out', _('Out'))], 'Move Type', default='all', required=True)

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
        attr_value = self.env['res.utility'].get_attribute_code_config()

        query = []
        if self.move_type in ('all', 'in'):
            query.append(f"""
select sm.id            as move_id,
       sm.quantity_done as qty_in,
       0                as qty_out
from stock_move sm
         left join stock_location sl1 on sm.location_id = sl1.id
         left join stock_warehouse wh1 on wh1.id = sl1.warehouse_id
         left join stock_location sl2 on sm.location_dest_id = sl2.id
         left join stock_warehouse wh2 on wh2.id = sl2.warehouse_id
where sm.state = 'done'
  and sm.company_id = any (array{allowed_company})
  and {format_date_query("sm.date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
  and sm.product_id = any (array {product_ids})
  and wh2.id = any (array {warehouse_ids})
""")
        if self.move_type in ('all', 'out'):
            query.append(f"""
select sm.id            as move_id,
       0                as qty_in,
       sm.quantity_done as qty_out
from stock_move sm
         left join stock_location sl1 on sm.location_id = sl1.id
         left join stock_warehouse wh1 on wh1.id = sl1.warehouse_id
         left join stock_location sl2 on sm.location_dest_id = sl2.id
         left join stock_warehouse wh2 on wh2.id = sl2.warehouse_id
where sm.state = 'done'
  and sm.company_id = any (array{allowed_company})
  and {format_date_query("sm.date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
  and sm.product_id = any (array {product_ids})
  and wh1.id = any (array {warehouse_ids})
""")

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
stock_moves as (
    select move_id,
       sum(qty_in)  as qty_in,
       sum(qty_out) as qty_out
       from ({' union all '.join(query)}) as moves
    group by move_id
)
select row_number() over ()                                                         as stt,
       to_char(sm.date + interval '{tz_offset} h', 'DD/MM/YYYY')                    as ngay,
       case when sp.transfer_id notnull then sp.origin else sp.name end             as so_ct,
       coalesce(wh1.name, sl1.name)                                                 as kho_xuat,
       coalesce(str.name, sp.origin, sm.reference)                                  as so_ct2,
       coalesce(wh2.name, sl2.name)                                                 as kho_nhap,
       rp.barcode                                                                   as ma_khach,
       rp.name                                                                      as ten_khach,
       ad.attrs::json -> '{attr_value.get('doi_tuong', '')}'                        as doi_tuong,
       split_part(cate.complete_name, ' / ', 2)                                     as nhom_hang,
       split_part(cate.complete_name, ' / ', 3)                                     as dong_hang,
       split_part(cate.complete_name, ' / ', 4)                                     as ket_cau,
       pp.barcode                                                                   as ma_vach,
       pt.sku_code                                                                  as ma_hang,
       coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')    as ten_hang,
       ad.attrs::json -> '{attr_value.get('mau_sac', '')}'                          as mau_sac,
       ad.attrs::json -> '{attr_value.get('size', '')}'                             as kich_co,
       ad.attrs::json -> '{attr_value.get('nam_san_xuat', '')}'                     as nam_sx,
       pt.collection                                                                as bo_suu_tap,
       ad.attrs::json -> '{attr_value.get('xuat_xu', '')}'                          as xuat_xu,
       ad.attrs::json -> '{attr_value.get('subclass1', '')}'                        as subclass1,
       ad.attrs::json -> '{attr_value.get('subclass2', '')}'                        as subclass2,
       ad.attrs::json -> '{attr_value.get('subclass3', '')}'                        as subclass3,
       ad.attrs::json -> '{attr_value.get('subclass4', '')}'                        as subclass4,
       ad.attrs::json -> '{attr_value.get('subclass5', '')}'                        as subclass5,
       coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')  as dv_tinh,
       sms.qty_in                                                                   as nhap,
       sms.qty_out                                                                  as xuat,
       pt.list_price                                                                as don_gia,
       acc.account_code                                                             as ma_loai,
       ''                                                                           as ngay_to_khai,
       sm.name                                                                      as dien_giai
from stock_move sm
    join stock_moves sms on sms.move_id = sm.id
    left join stock_picking sp on sm.picking_id = sp.id
    left join stock_transfer st on sp.transfer_id = st.id
    left join stock_transfer_request str on st.stock_request_id = str.id
    left join res_partner rp on sp.partner_id = rp.id
    left join stock_location sl1 on sm.location_id = sl1.id
    left join stock_warehouse wh1 on wh1.id = sl1.warehouse_id
    left join stock_location sl2 on sm.location_dest_id = sl2.id
    left join stock_warehouse wh2 on wh2.id = sl2.warehouse_id
    left join product_product pp on pp.id = sm.product_id
    left join product_template pt on pt.id = pp.product_tmpl_id
    left join uom_uom uom on uom.id = sm.product_uom
    join product_category cate on cate.id = pt.categ_id
    left join account_by_categ_id acc on acc.cate_id = cate.id
    left join attribute_data ad on ad.product_id = pp.id
order by stt
"""
        return query_final

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Product = self.env['product.product']
        Utility = self.env['res.utility']
        categ_ids = self.texture_ids or self.product_line_ids or self.product_group_ids or self.product_brand_id
        if self.product_ids:
            product_ids = self.product_ids.ids
        elif categ_ids:
            product_ids = Product.search([('categ_id', 'in', Utility.get_all_category_last_level(categ_ids))]).ids or [-1]
        else:
            product_ids = [-1]
        warehouse_ids = self.warehouse_ids.ids if self.warehouse_ids else (self.env['stock.warehouse'].search([('company_id', 'in', allowed_company)]).ids or [-1])
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
        sheet = workbook.add_worksheet('Báo cáo chi tiết xuất nhập hàng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo chi tiết xuất nhập hàng', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày %s' % self.from_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 2, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ngay'), formats.get('center_format'))
            sheet.write(row, 2, value.get('so_ct'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('kho_xuat'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('so_ct2'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('kho_nhap'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ma_khach'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('ten_khach'), formats.get('normal_format'))
            sheet.write(row, 8, ', '.join(value.get('doi_tuong') or []), formats.get('normal_format'))
            sheet.write(row, 9, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('ma_vach'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('ma_hang'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('ten_hang'), formats.get('normal_format'))
            sheet.write(row, 15, ', '.join(value.get('mau_sac') or []), formats.get('normal_format'))
            sheet.write(row, 16, ', '.join(value.get('kich_co') or []), formats.get('normal_format'))
            sheet.write(row, 17, ', '.join(value.get('nam_sx') or []), formats.get('normal_format'))
            sheet.write(row, 18, value.get('bo_suu_tap'), formats.get('normal_format'))
            sheet.write(row, 19, ', '.join(value.get('xuat_xu') or []), formats.get('normal_format'))
            sheet.write(row, 20, ', '.join(value.get('subclass1') or []), formats.get('normal_format'))
            sheet.write(row, 21, ', '.join(value.get('subclass2') or []), formats.get('normal_format'))
            sheet.write(row, 22, ', '.join(value.get('subclass3') or []), formats.get('normal_format'))
            sheet.write(row, 23, ', '.join(value.get('subclass4') or []), formats.get('normal_format'))
            sheet.write(row, 24, ', '.join(value.get('subclass5') or []), formats.get('normal_format'))
            sheet.write(row, 25, value.get('dv_tinh'), formats.get('normal_format'))
            sheet.write(row, 26, value.get('nhap'), formats.get('normal_format'))
            sheet.write(row, 27, value.get('xuat'), formats.get('normal_format'))
            sheet.write(row, 28, value.get('don_gia'), formats.get('int_number_format'))
            sheet.write(row, 29, value.get('ma_loai'), formats.get('normal_format'))
            sheet.write(row, 30, value.get('ngay_to_khai'), formats.get('normal_format'))
            sheet.write(row, 31, value.get('dien_giai'), formats.get('normal_format'))
            row += 1
