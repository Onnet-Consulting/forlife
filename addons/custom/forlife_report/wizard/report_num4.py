# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = ['STT', 'Mã Hàng', 'Tên Hàng', 'Nhóm hàng', 'Màu', 'Size', 'Bộ sưu tập', 'Kết cấu', 'Dòng hàng', 'SL cuối kỳ']
COLUMN_WIDTHS = [8, 20, 30, 20, 15, 10, 30, 20, 20, 20]


class ReportNum4(models.TransientModel):
    _name = 'report.num4'
    _inherit = 'report.base'
    _description = 'Report stock by product'

    to_date = fields.Date(string='To date', required=True, default=fields.Date.context_today)
    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    product_ids = fields.Many2many('product.product', string='Products', domain=[('type', '=', 'product')])
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    product_brand_id = fields.Many2one('product.category', string='Brand', domain="[('parent_id', '=', False)]")
    product_group_ids = fields.Many2many('product.category', 'num4_product_group_rel', 'num4_id', 'product_group_id', string='Product Group')
    product_line_ids = fields.Many2many('product.category', 'num4_product_line_rel', 'num4_id', 'product_line_id', string='Product Line')
    product_texture_ids = fields.Many2many('product.category', 'num4_product_texture_rel', 'num4_id', 'product_texture_id', string='Product Texture')

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

        where_query = """
            sm.company_id = %s
            and sm.state = 'done'
            and pt.type = 'product'\n
        """ % self.company_id.id
        if warehouse_ids:
            where_query += f"and (src_wh.id = any (array{warehouse_ids.ids}) or des_wh.id = any (array{warehouse_ids.ids}))\n"
        if product_ids:
            where_query += f"and sm.product_id = any (array{product_ids})\n"
        if self.to_date:
            where_query += f"""and {format_date_query("sm.date", tz_offset)} <= '{str(self.to_date)}'\n"""
        where_query += f" and pci.brand_id = {self.product_brand_id.id}\n"
        if self.product_group_ids:
            where_query += f" and pci.product_group_id = any (array{self.product_group_ids.ids})\n"
        if self.product_line_ids:
            where_query += f" and pci.product_line_id = any (array{self.product_line_ids.ids})\n"
        if self.product_texture_ids:
            where_query += f" and pci.texture_id = any (array{self.product_texture_ids.ids})\n"

        query = f"""
with product_cate_info as -- lấy ID của Thương hiệu, nhóm hàng, dòng hàng, kết cấu, tên sản phẩm, tên ĐVT, barcode theo ID sản phẩm
    (select 
        pp.id     		                                                          as product_id,
        texture.id 		                                                          as texture_id,
        product_line.id                                                           as product_line_id,
        product_group.id                                                          as product_group_id,
        brand.id 		                                                          as brand_id,
        texture.complete_name                                                     as complete_name,
        pp.barcode                                                                as product_barcode,
        coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US')   as product_name
    from product_product pp 
        left join product_template pt on pt.id = pp.product_tmpl_id
        join product_category texture on texture.id = pt.categ_id
        join product_category product_line on product_line.id = texture.parent_id
        join product_category product_group on product_group.id = product_line.parent_id
        join product_category brand on brand.id = product_group.parent_id
    where pp.id = any (array{product_ids})
    ),
stock as 
    (select 
        sm.product_id                                                                            as product_id,
        sum(case when coalesce(src_wh.id, 0) <> 0 then -sm.product_qty else sm.product_qty end)  as qty
    from stock_move sm
        left join stock_location des_lc on sm.location_dest_id = des_lc.id
        left join product_product pp on sm.product_id = pp.id
        left join product_template pt on pp.product_tmpl_id = pt.id
        left join stock_warehouse des_wh on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
        left join stock_location src_lc on sm.location_id = src_lc.id
        left join stock_warehouse src_wh on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
        left join product_cate_info pci on pci.product_id = pp.id
    where {where_query}
    group by sm.product_id
    )
select row_number() over ()                                                                                     as num,
       (select product_barcode from product_cate_info where product_id = stock.product_id)                      as product_barcode,
       (select product_name from product_cate_info where product_id = stock.product_id)                         as product_name,
       (select split_part(complete_name, ' / ', 2) from product_cate_info where product_id = stock.product_id)  as product_group,
       (select split_part(complete_name, ' / ', 3) from product_cate_info where product_id = stock.product_id)  as product_line,
       (select split_part(complete_name, ' / ', 4) from product_cate_info where product_id = stock.product_id)  as texture,
       ''                                                                                                       as collection,
       ''                                                                                                       as color,
       ''                                                                                                       as size,
       stock.qty                                                                                                as total_qty
from stock
order by num
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

    def generate_xlsx_report(self, workbook):
        data = self.get_data()
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tồn kho')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo tồn kho theo sản phẩm', formats.get('header_format'))
        sheet.write(2, 0, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 2, 'Thương hiệu: %s' % self.product_brand_id.name, formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, COLUMN_WIDTHS[idx])
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('product_group'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('color'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('size'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('collection'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('texture'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('product_line'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('total_qty'), formats.get('float_number_format'))
            row += 1
