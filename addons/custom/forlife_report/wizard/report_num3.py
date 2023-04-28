# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = ['STT', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu', 'Mùa hàng', 'Giới tính', 'Mã SP',
          'Tên SP', 'Đơn vị', 'Màu sắc', 'Kích cỡ', 'Nhãn hiệu', 'Tổng tồn', 'Hàng treo']
COLUMN_WIDTHS = [8, 20, 20, 20, 20, 20, 20, 30, 20, 20, 20, 20, 20, 20]


class ReportNum3(models.TransientModel):
    _name = 'report.num3'
    _inherit = 'report.base'
    _description = 'Report stock in time range by warehouse'

    to_date = fields.Date(string='To date', required=True, default=fields.Date.context_today)
    report_by = fields.Selection([('branch', _('Branch')), ('area', _('Area'))], 'Report by', required=True, default='branch')
    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=True)
    all_areas = fields.Boolean(string='All areas', default=True)
    defective_inventory = fields.Boolean(string='Skip defective inventory')
    order_inventory = fields.Boolean(string='Skip order inventory')
    product_ids = fields.Many2many('product.product', string='Products', domain=[('type', '=', 'product')])
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    area_ids = fields.Many2many('res.location.province', string='Areas')
    product_brand_id = fields.Many2one('product.category', string='Brand', domain="[('parent_id', '=', False), ('category_type_id', '!=', False)]")
    product_group_ids = fields.Many2many('product.category', 'num3_product_group_rel', 'num3_id', 'product_group_id', string='Product Group')
    product_line_ids = fields.Many2many('product.category', 'num3_product_line_rel', 'num3_id', 'product_line_id', string='Product Line')
    product_texture_ids = fields.Many2many('product.category', 'num3_product_texture_rel', 'num3_id', 'product_texture_id', string='Product Texture')

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

        if self.report_by == 'area':
            stock_query = f"""select 
        sm.product_id          as product_id,
        coalesce(srlp.id, case when coalesce(src_wh.id, 0) <> 0 then -1 else 0 end) as src_warehouse_id,
        coalesce(drlp.id, case when coalesce(des_wh.id, 0) <> 0 then -1 else 0 end) as dest_warehouse_id,
        sum(sm.product_qty)    as qty
    from stock_move sm
        left join stock_location des_lc on sm.location_dest_id = des_lc.id
        left join product_product pp on sm.product_id = pp.id
        left join product_template pt on pp.product_tmpl_id = pt.id
        left join stock_warehouse des_wh on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
        left join res_location_province drlp on drlp.id = des_wh.loc_province_id
        left join stock_location src_lc on sm.location_id = src_lc.id
        left join stock_warehouse src_wh on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
        left join res_location_province srlp on srlp.id = src_wh.loc_province_id
        left join product_cate_info pci on pci.product_id = pp.id
    where {where_query}
    group by sm.product_id, src_warehouse_id, dest_warehouse_id
            """
        else:
            stock_query = f"""select 
        sm.product_id          as product_id,
        coalesce(src_wh.id, 0) as src_warehouse_id,
        coalesce(des_wh.id, 0) as dest_warehouse_id,
        sum(sm.product_qty)    as qty
    from stock_move sm
        left join stock_location des_lc on sm.location_dest_id = des_lc.id
        left join product_product pp on sm.product_id = pp.id
        left join product_template pt on pp.product_tmpl_id = pt.id
        left join stock_warehouse des_wh on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
        left join stock_location src_lc on sm.location_id = src_lc.id
        left join stock_warehouse src_wh on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
        left join product_cate_info pci on pci.product_id = pp.id
    where {where_query}
    group by sm.product_id, src_wh.id, des_wh.id            
                """

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
        coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US')   as product_name,
        coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US') as uom_name
    from product_product pp 
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join uom_uom uom on pt.uom_id = uom.id
        join product_category xxx on xxx.id = pt.categ_id
        join product_category texture on texture.id = xxx.id
        join product_category product_line on product_line.id = texture.parent_id
        join product_category product_group on product_group.id = product_line.parent_id
        join product_category brand on brand.id = product_group.parent_id
    where pp.id = any (array{product_ids})
    ),
stock as 
    ({stock_query}
    ),
source_stock as 
    (select product_id,
        src_warehouse_id as warehouse_id,
        sum(qty)         as qty
    from stock
    where src_warehouse_id != 0
    group by product_id, src_warehouse_id
    ),
agg_source_stock as 
    (select product_id,
        json_object_agg(warehouse_id, qty) as qty_by_wh
    from source_stock
    group by product_id
    ),
destination_stock as 
    (select product_id,
        dest_warehouse_id as warehouse_id,
        sum(qty)          as qty
    from stock
    where dest_warehouse_id != 0
    group by product_id, dest_warehouse_id
    ),
agg_destination_stock as 
    (select product_id,
        json_object_agg(warehouse_id, qty) as qty_by_wh
    from destination_stock
    group by product_id
    )
select row_number() over ()                                               as num,
       coalesce(aggs.product_id, aggd.product_id)                         as product_id,
       (select product_barcode from product_cate_info
        where product_id = coalesce(aggs.product_id, aggd.product_id))    as product_barcode,
       (select product_name from product_cate_info
        where product_id = coalesce(aggs.product_id, aggd.product_id))    as product_name,
       (select uom_name from product_cate_info
        where product_id = coalesce(aggs.product_id, aggd.product_id))    as uom_name,
       aggs.qty_by_wh                                                     as source_qty_by_wh,
       aggd.qty_by_wh                                                     as destination_qty_by_wh,
       (select split_part(complete_name, ' / ', 2) from product_cate_info
        where product_id = coalesce(aggs.product_id, aggd.product_id))    as product_group,
       (select split_part(complete_name, ' / ', 3) from product_cate_info
        where product_id = coalesce(aggs.product_id, aggd.product_id))    as product_line,
       (select split_part(complete_name, ' / ', 4) from product_cate_info
        where product_id = coalesce(aggs.product_id, aggd.product_id))    as texture,
       ''                                                                 as season,
       ''                                                                 as gender,
       ''                                                                 as color,
       ''                                                                 as size,
       ''                                                                 as label,
       ''                                                                 as total_pending
from agg_source_stock aggs
     full join agg_destination_stock aggd on aggs.product_id = aggd.product_id
order by num
            """
        return query

    def get_warehouse_data(self, warehouse_ids):
        if self.report_by == 'area':
            data = warehouse_ids.mapped('loc_province_id')
        else:
            data = warehouse_ids
        warehouse_ids = []
        warehouse_names = []
        warehouse_name_by_id = {}
        for warehouse in data:
            wh_name = warehouse['name']
            wh_id = str(warehouse['id'])
            warehouse_ids.append(wh_id)
            warehouse_names.append(wh_name)
            warehouse_name_by_id[wh_id] = wh_name
        return dict(
            warehouse_name_by_id=warehouse_name_by_id,
            warehouse_names=warehouse_names,
            warehouse_ids=warehouse_ids
        )

    def format_data(self, data):
        for line in data:
            source_warehouse_qty = line.pop('source_qty_by_wh') or {}
            destination_warehouse_qty = line.pop('destination_qty_by_wh') or {}
            product_qty_by_warehouse = {}
            total_qty = 0
            warehouse_ids = {**source_warehouse_qty, **destination_warehouse_qty}.keys()
            for wh_id in warehouse_ids:
                wh_qty = destination_warehouse_qty.get(wh_id, 0) - source_warehouse_qty.get(wh_id, 0)
                product_qty_by_warehouse[wh_id] = wh_qty
                total_qty += wh_qty

            line['product_qty_by_warehouse'] = product_qty_by_warehouse
            line['total_qty'] = total_qty
        return data

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        stock_wh = self.env['stock.warehouse']
        product_ids = (self.env['product.product'].search([('type', '=', 'product')]).ids or [-1]) if self.all_products else self.product_ids.ids
        if self.report_by == 'area':
            warehouse_ids = stock_wh.search([('loc_province_id', '!=', False)]) if self.all_areas else (stock_wh.search(
                [('loc_province_id', 'in', self.area_ids.ids)]) if self.area_ids else stock_wh.search([('loc_province_id', '=', False)]))
            if not warehouse_ids:
                raise ValidationError(_('Warehouse not found !'))
        else:
            warehouse_ids = stock_wh.search([]) if self.all_warehouses else self.warehouse_ids
        query = self._get_query(product_ids, warehouse_ids)
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        data = self.format_data(data)
        warehouse_data = self.get_warehouse_data(warehouse_ids)
        values.update({
            'titles': TITLES + warehouse_data['warehouse_names'],
            "data": data,
            **warehouse_data
        })
        return values

    def generate_xlsx_report(self, workbook):
        data = self.get_data()
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tồn kho')
        columns = COLUMN_WIDTHS + [20] * len(data['warehouse_names'])
        sheet.set_row(0, 25)
        report_by = 'khu vực' if self.report_by == 'area' else 'chi nhánh'
        sheet.write(0, 0, 'Báo cáo tồn kho theo %s' % report_by, formats.get('header_format'))
        sheet.write(2, 0, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 2, 'Thương hiệu: %s' % self.product_brand_id.name, formats.get('italic_format'))
        for idx, title in enumerate(TITLES + data['warehouse_names']):
            sheet.write(4, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, columns[idx])
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value['num'], formats.get('center_format'))
            sheet.write(row, 1, value['product_group'], formats.get('normal_format'))
            sheet.write(row, 2, value['product_line'], formats.get('normal_format'))
            sheet.write(row, 3, value['texture'], formats.get('normal_format'))
            sheet.write(row, 4, value['season'], formats.get('normal_format'))
            sheet.write(row, 5, value['gender'], formats.get('normal_format'))
            sheet.write(row, 6, value['product_barcode'], formats.get('normal_format'))
            sheet.write(row, 7, value['product_name'], formats.get('normal_format'))
            sheet.write(row, 8, value['uom_name'], formats.get('normal_format'))
            sheet.write(row, 9, value['color'], formats.get('normal_format'))
            sheet.write(row, 10, value['size'], formats.get('normal_format'))
            sheet.write(row, 11, value['label'], formats.get('normal_format'))
            sheet.write(row, 12, value['total_qty'], formats.get('float_number_format'))
            sheet.write(row, 13, value['total_pending'], formats.get('float_number_format'))
            col = 14
            for i in data['warehouse_ids']:
                sheet.write(row, col, value['product_qty_by_warehouse'].get(i), formats.get('float_number_format'))
                col += 1
            row += 1
