# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = ['STT', 'Thương hiệu', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu', 'Mùa hàng', 'Giới tính',
          'Mã SP', 'Tên SP', 'Đơn vị', 'Màu sắc', 'Kích cỡ', 'Tổng tồn', 'Hàng treo']
COLUMN_WIDTHS = [8, 20, 20, 20, 20, 20, 20, 20, 30, 20, 20, 20, 20, 20]


class ReportNum3(models.TransientModel):
    _name = 'report.num3'
    _inherit = 'report.base'
    _description = 'Report stock in time range by warehouse'

    to_date = fields.Date(string='To date', required=True, default=fields.Date.context_today)
    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=True)
    product_ids = fields.Many2many('product.product', string='Products', domain=[('type', '=', 'product')])
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    product_brand_ids = fields.Many2many('product.category', 'num3_product_brand_rel', 'num3_id', 'brand_id', string='Brand', domain="[('parent_id', '=', False)]")
    product_group_ids = fields.Many2many('product.category', 'num3_product_group_rel', 'num3_id', 'product_group_id', string='Product Group')
    product_line_ids = fields.Many2many('product.category', 'num3_product_line_rel', 'num3_id', 'product_line_id', string='Product Line')
    product_texture_ids = fields.Many2many('product.category', 'num3_product_texture_rel', 'num3_id', 'product_texture_id', string='Product Texture')

    @api.onchange('product_brand_ids')
    def onchange_product_brand(self):
        self.product_group_ids = self.product_group_ids.filtered(lambda f: f.parent_id in self.product_brand_ids.ids)
        return {'domain': {'product_group_ids': [('parent_id', 'in', self.product_brand_ids.ids)]}}

    @api.onchange('product_group_ids')
    def onchange_product_group(self):
        self.product_line_ids = self.product_line_ids.filtered(lambda f: f.parent_id in self.product_group_ids.ids)
        return {'domain': {'product_line_ids': [('parent_id', 'in', self.product_group_ids.ids)]}}

    @api.onchange('product_line_ids')
    def onchange_product_line(self):
        self.product_texture_ids = self.product_texture_ids.filtered(lambda f: f.parent_id in self.product_line_ids.ids)
        return {'domain': {'product_texture_ids': [('parent_id', 'in', self.product_line_ids.ids)]}}

    def view_report(self):
        self.ensure_one()
        action = self.env.ref('forlife_report.report_num_3_client_action').read()[0]
        return action

    def _get_query_params(self):
        self.ensure_one()
        params = [self.company_id.id]
        if not self.all_warehouses and self.warehouse_ids:
            params.extend([self.warehouse_ids.ids] * 2)
        if not self.all_products and self.product_ids:
            params.append(self.product_ids.ids)
        if self.to_date:
            params.append(self.to_date)
        return params

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset

        where_query = """
            sm.company_id = %s
            and sm.state = 'done'
            and pt.type = 'product'\n
        """
        if not self.all_warehouses and self.warehouse_ids:
            warehouse_conditions = "(src_wh.id = any (%s) or des_wh.id = any (%s))"
            where_query += f"and {warehouse_conditions}\n"
        if not self.all_products and self.product_ids:
            product_conditions = "sm.product_id = any (%s)"
            where_query += f"and {product_conditions}\n"
        if self.to_date:
            where_query += f"""and {format_date_query("sm.date", tz_offset)} <= %s\n"""
        product_cate_join = ''
        if any([self.product_brand_ids.ids, self.product_group_ids.ids, self.product_line_ids.ids, self.product_texture_ids.ids]):
            product_cate_join = 'left join product_cate_info pci on pci.product_id = pp.id\n'
            if self.product_brand_ids:
                where_query += f" and pci.brand_id = any (array{self.product_brand_ids.ids})\n"
            if self.product_group_ids:
                where_query += f" and pci.product_group_id = any (array{self.product_group_ids.ids})\n"
            if self.product_line_ids:
                where_query += f" and pci.product_line_id = any (array{self.product_line_ids.ids})\n"
            if self.product_texture_ids:
                where_query += f" and pci.texture_id = any (array{self.product_texture_ids.ids})\n"

        query = f"""
with product_cate_info as 
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
        join product_category texture on texture.id = pt.categ_id
        join product_category product_line on product_line.id = texture.parent_id
        join product_category product_group on product_group.id = product_line.parent_id
        join product_category brand on brand.id = product_group.parent_id
    ),
stock as 
    (select 
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
        {product_cate_join}
    where {where_query}
    group by sm.product_id, src_wh.id, des_wh.id
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
       (select split_part(complete_name, ' / ', 1) from product_cate_info
        where product_id = coalesce(aggs.product_id, aggd.product_id))    as brand,
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
       ''                                                                 as total_pending
from agg_source_stock aggs
     full join agg_destination_stock aggd on aggs.product_id = aggd.product_id
order by num
        """
        return query

    def get_warehouse_data(self):
        query = """
            select id,name from stock_warehouse where company_id = %s
        """
        params = [self.company_id.id]
        if not self.all_warehouses and self.warehouse_ids:
            query += "\n and id = any (%s)"
            params.append([self.warehouse_ids.ids])

        self._cr.execute(query, params)
        data = self._cr.dictfetchall()
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
        query = self._get_query()
        params = self._get_query_params()
        self._cr.execute(query, params)
        data = self._cr.dictfetchall()
        data = self.format_data(data)
        warehouse_data = self.get_warehouse_data()
        return {
            'titles': TITLES + warehouse_data['warehouse_names'],
            "data": data,
            **warehouse_data
        }

    def generate_xlsx_report(self, workbook):
        data = self.get_data()
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tồn kho - chi nhánh')
        columns = COLUMN_WIDTHS + [20] * len(data['warehouse_names'])
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo tồn kho - chi nhánh', formats.get('header_format'))
        sheet.write(2, 0, _('To date: %s') % self.to_date.strftime('%d/%m/%Y'), formats.get('normal_format'))
        for idx, title in enumerate(TITLES + data['warehouse_names']):
            sheet.write(4, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, columns[idx])
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value['num'], formats.get('center_format'))
            sheet.write(row, 1, value['brand'], formats.get('normal_format'))
            sheet.write(row, 2, value['product_group'], formats.get('normal_format'))
            sheet.write(row, 3, value['product_line'], formats.get('normal_format'))
            sheet.write(row, 4, value['texture'], formats.get('normal_format'))
            sheet.write(row, 5, value['season'], formats.get('normal_format'))
            sheet.write(row, 6, value['gender'], formats.get('normal_format'))
            sheet.write(row, 7, value['product_barcode'], formats.get('normal_format'))
            sheet.write(row, 8, value['product_name'], formats.get('normal_format'))
            sheet.write(row, 9, value['uom_name'], formats.get('normal_format'))
            sheet.write(row, 10, value['color'], formats.get('normal_format'))
            sheet.write(row, 11, value['size'], formats.get('normal_format'))
            sheet.write(row, 12, value['total_qty'], formats.get('float_number_format'))
            sheet.write(row, 13, value['total_pending'], formats.get('float_number_format'))
            col = 14
            for i in data['warehouse_ids']:
                sheet.write(row, col, value['product_qty_by_warehouse'].get(i), formats.get('float_number_format'))
                col += 1
            row += 1
