# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Ngày', 'Số CT', 'Kho', 'Số CT2', 'Kho2', 'Mã khách', 'Tên khách', 'Đối tượng', 'Nhóm hàng',
    'Dòng hàng', 'Kết cấu', 'Mã vạch', 'Mã hàng', 'Tên hàng', 'Màu sắc', 'Kích cỡ', 'Năm sản xuất', 'Bộ sưu tập',
    'Xuất xứ', 'Các thuộc tính', 'Đơn vị tính', 'Nhập', 'Xuất', 'Mã loại', 'Ngày tờ khai', 'Diễn giải',
]


class ReportNum16(models.TransientModel):
    _name = 'report.num16'
    _inherit = 'report.base'
    _description = 'Report stock move'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    product_ids = fields.Many2many('product.product', string='Products', domain=[('type', '=', 'product')])
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    product_brand_id = fields.Many2one('product.category', string='Brand', domain="[('parent_id', '=', False)]")
    product_group_ids = fields.Many2many('product.category', 'num16_product_group_rel', 'num16_id', 'product_group_id', string='Product Group')
    product_line_ids = fields.Many2many('product.category', 'num16_product_line_rel', 'num16_id', 'product_line_id', string='Product Line')
    product_texture_ids = fields.Many2many('product.category', 'num16_product_texture_rel', 'num16_id', 'product_texture_id', string='Product Texture')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('product_brand_id')
    def onchange_product_brand(self):
        self.product_group_ids = self.product_group_ids.filtered(lambda f: f.parent_id == self.product_brand_id.id)

    @api.onchange('product_group_ids')
    def onchange_product_group(self):
        self.product_line_ids = self.product_line_ids.filtered(lambda f: f.parent_id in self.product_group_ids.ids)

    @api.onchange('product_line_ids')
    def onchange_product_line(self):
        self.product_texture_ids = self.product_texture_ids.filtered(lambda f: f.parent_id in self.product_line_ids.ids)

    def _get_query(self, product_ids, warehouse_ids):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset

        where_query = f""" where
            sm.company_id = {self.company_id.id}
            and sm.state = 'done'
            and {format_date_query("sm.date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
            and sm.product_id = any (array{product_ids})
            and (src_wh.id = any (array{warehouse_ids}) or des_wh.id = any (array{warehouse_ids}))
            and pci.brand_id = {self.product_brand_id.id}\n
        """
        if self.product_group_ids:
            where_query += f" and pci.product_group_id = any (array{self.product_group_ids.ids})\n"
        if self.product_line_ids:
            where_query += f" and pci.product_line_id = any (array{self.product_line_ids.ids})\n"
        if self.product_texture_ids:
            where_query += f" and pci.texture_id = any (array{self.product_texture_ids.ids})\n"

        query = f"""
with account_by_categ_id as ( -- lấy mã tài khoản định giá tồn kho bằng cate_id
    select 
        cate.id as cate_id,
        aa.code as account_code
    from product_category cate
        left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
        left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
    where  ir.name='property_stock_valuation_account_id' and ir.company_id = {self.company_id.id}
    order by cate.id 
),
product_cate_info as (
    select 
        pp.id     		                                                          as product_id,
        texture.id 		                                                          as texture_id,
        product_line.id                                                           as product_line_id,
        product_group.id                                                          as product_group_id,
        brand.id 		                                                          as brand_id,
        texture.complete_name                                                     as complete_name,
        pp.barcode                                                                as product_barcode,
        pp.default_code                                                           as internal_ref,
        coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US')   as product_name,
        (select account_code from account_by_categ_id where cate_id = texture.id) as account_code
    from product_product pp 
        left join product_template pt on pt.id = pp.product_tmpl_id
        join product_category texture on texture.id = pt.categ_id
        join product_category product_line on product_line.id = texture.parent_id
        join product_category product_group on product_group.id = product_line.parent_id
        join product_category brand on brand.id = product_group.parent_id
    where pp.id = any (array{product_ids})
)
select to_char(sm.date, 'DD/MM/YYYY') as date,
       '' as so_ct,
       '' as wh_name,
       '' as so_ct2,
       '' as wh_name2,
       '' as ma_khach,
       '' as ten_khach,
       '' as doi_tuong,
       split_part(pci.complete_name, ' / ', 2) as nhom_hang,
       split_part(pci.complete_name, ' / ', 3) as dong_hang,
       split_part(pci.complete_name, ' / ', 4) as ket_cau,
       pci.product_barcode as ma_vach,
       pci.internal_ref as ma_hang,
       pci.product_name as ten_hang,
       '' as mau_sac,
       '' as kich_co,
       '' as nam_sx,
       '' as bo_suu_tap,
       '' as xuat_xu,
       '' as cac_thuoc_tinh,
       coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US') as dv_tinh,
       sm.quantity_done as nhap,
       sm.quantity_done as xuat,
       pci.account_code as ma_loai,
       '' as ngay_to_khai,
       sm.name as dien_giai
from stock_move sm
    left join uom_uom uom on uom.id = sm.product_uom
    left join stock_location des_lc on sm.location_dest_id = des_lc.id
    left join stock_warehouse des_wh on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
    left join stock_location src_lc on sm.location_id = src_lc.id
    left join stock_warehouse src_wh on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
    left join product_cate_info pci on pci.product_id = sm.product_id
{where_query}
"""
        return query

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        stock_wh = self.env['stock.warehouse']
        product_ids = (self.env['product.product'].search([]).ids or [-1]) if self.all_products else self.product_ids.ids
        warehouse_ids = (stock_wh.search([]).ids or [-1]) if self.all_warehouses else self.warehouse_ids.ids
        query = self._get_query(product_ids, warehouse_ids)
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values
