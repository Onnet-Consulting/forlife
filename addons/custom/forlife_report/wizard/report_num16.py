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

        where_query = f"""
            sm.company_id = {self.company_id.id}
            and sm.state = 'done'
            and {format_date_query("sm.date", tz_offset)} between '{self.from_date}' and '{self.to_date}'\n
        """
        if warehouse_ids:
            where_query += f"and (src_wh.id = any (array{warehouse_ids.ids}) or des_wh.id = any (array{warehouse_ids.ids}))\n"
        if product_ids:
            where_query += f"and sm.product_id = any (array{product_ids})\n"
        where_query += f" and pci.brand_id = {self.product_brand_id.id}\n"
        # if self.product_group_ids:
        #     where_query += f" and pci.product_group_id = any (array{self.product_group_ids.ids})\n"
        # if self.product_line_ids:
        #     where_query += f" and pci.product_line_id = any (array{self.product_line_ids.ids})\n"
        # if self.product_texture_ids:
        #     where_query += f" and pci.texture_id = any (array{self.product_texture_ids.ids})\n"

        query = f"""
select to_char(date, 'DD/MM/YYYY') as date,
       '' as so_ct,
       '' as wh_name,
       '' as so_ct2,
       '' as wh_name2,
       '' as ma_khach,
       '' as ten_khach,
       '' as doi_tuong,
       '' as nhom_hang,
       '' as dong_hang,
       '' as ket_cau,
       '' as ma_vach,
       '' as ma_hang,
       '' as ten_hang,
       '' as mau_sac,
       '' as kich_co,
       '' as nam_sx,
       '' as bo_suu_tap,
       '' as xuat_xu,
       '' as cac_thuoc_tinh,
       '' as dv_tinh,
       '' as nhap,
       '' as xuat,
       '' as ma_loai,
       '' as ngay_to_khai,
       '' as dien_giai
from stock_move
"""
        return query

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        stock_wh = self.env['stock.warehouse']
        product_ids = self.env['product.product'].search([]).ids if self.all_products else self.product_ids.ids
        warehouse_ids = stock_wh.search([]) if self.all_warehouses else self.warehouse_ids
        query = self._get_query(product_ids, warehouse_ids)
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values
