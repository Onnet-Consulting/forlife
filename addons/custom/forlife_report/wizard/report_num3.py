# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.tools.safe_eval import safe_eval

TITLES = ['STT', 'Thương hiệu', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu', 'Mùa hàng', 'Giới tính', 'Mã SP',
          'Tên SP', 'Đơn vị', 'Màu sắc', 'Kích cỡ', 'Nhãn hiệu', 'Tổng tồn', 'Hàng treo']
COLUMN_WIDTHS = [8, 20, 20, 20, 20, 20, 20, 20, 30, 20, 20, 20, 20, 20, 20]


class ReportNum3(models.TransientModel):
    _name = 'report.num3'
    _inherit = 'report.base'
    _description = 'Report stock in time range by warehouse'

    to_date = fields.Date(string='To date', required=True, default=fields.Date.context_today)
    report_by = fields.Selection([('branch', _('Branch')), ('area', _('Area'))], 'Report by', required=True, default='branch')
    product_domain = fields.Char('Product', default='[]')
    warehouse_domain = fields.Char('Warehouse', default='[]')
    defective_inventory = fields.Boolean(string='Skip defective inventory')
    order_inventory = fields.Boolean(string='Skip order inventory')
    all_areas = fields.Boolean(string='All areas', default=True)
    area_ids = fields.Many2many('res.location.province', string='Areas')

    def _get_query(self, product_ids, warehouse_ids, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        attr_value = self.env['res.utility'].get_attribute_code_config()

        where_query = f"""
            sm.company_id = any (array{allowed_company})
            and sm.state = 'done'
            and (src_wh.id = any (array{warehouse_ids}) or des_wh.id = any (array{warehouse_ids}))
            and sm.product_id = any (array{product_ids})\n
        """
        if self.to_date:
            where_query += f"""and {format_date_query("sm.date", tz_offset)} <= '{self.to_date}'\n"""

        if self.report_by == 'area':
            stock_query = f"""select 
    sm.product_id                                                               as product_id,
    coalesce(srlp.id, case when coalesce(src_wh.id, 0) <> 0 then -1 else 0 end) as src_warehouse_id,
    coalesce(drlp.id, case when coalesce(des_wh.id, 0) <> 0 then -1 else 0 end) as dest_warehouse_id,
    sum(sm.product_qty)                                                         as qty
from stock_move sm
    left join stock_location des_lc on sm.location_dest_id = des_lc.id
    left join product_product pp on sm.product_id = pp.id
    left join product_template pt on pp.product_tmpl_id = pt.id
    left join stock_warehouse des_wh on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
    left join res_location_province drlp on drlp.id = des_wh.loc_province_id
    left join stock_location src_lc on sm.location_id = src_lc.id
    left join stock_warehouse src_wh on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
    left join res_location_province srlp on srlp.id = src_wh.loc_province_id
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
where {where_query}
group by sm.product_id, src_wh.id, des_wh.id            
"""

        query = f"""
with attribute_data as (
    select product_id                         as product_id,
           json_object_agg(attrs_code, value) as attrs
    from (
        select 
            pp.id                                                                                   as product_id,
            pa.attrs_code                                                                           as attrs_code,
            array_agg(coalesce(pav.name::json -> '{user_lang_code}', pav.name::json -> 'en_US'))    as value
        from product_template_attribute_line ptal
            left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
            left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
            left join product_attribute pa on ptal.attribute_id = pa.id
            left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
        where pp.id = any (array{product_ids}) and pa.attrs_code notnull
        group by pp.id, pa.attrs_code) as att
    group by product_id
), 
product_cate_info as (
    select 
        pp.id     		                                                          as product_id,
        cate.complete_name                                                        as complete_name,
        pp.barcode                                                                as product_barcode,
        coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US')   as product_name,
        coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US') as uom_name,
        ad.attrs::json -> '{attr_value.get('size', '')}'                          as size,
        ad.attrs::json -> '{attr_value.get('mau_sac', '')}'                       as color,
        ad.attrs::json -> '{attr_value.get('mua_vu', '')}'                        as season,
        ad.attrs::json -> '{attr_value.get('doi_tuong', '')}'                     as gender,
        ad.attrs::json -> '{attr_value.get('nhan_hieu', '')}'                     as label
    from product_product pp 
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join uom_uom uom on pt.uom_id = uom.id
        join product_category cate on cate.id = pt.categ_id
        left join attribute_data ad on ad.product_id = pp.id
    where pp.id = any (array{product_ids})
),
stock as (
    {stock_query}
),
source_stock as (
    select product_id,
        src_warehouse_id as warehouse_id,
        sum(qty)         as qty
    from stock
    where src_warehouse_id != 0
    group by product_id, src_warehouse_id
),
agg_source_stock as (
    select product_id,
        json_object_agg(warehouse_id, qty) as qty_by_wh
    from source_stock
    group by product_id
),
destination_stock as (
    select product_id,
        dest_warehouse_id as warehouse_id,
        sum(qty)          as qty
    from stock
    where dest_warehouse_id != 0
    group by product_id, dest_warehouse_id
),
agg_destination_stock as (
    select product_id,
        json_object_agg(warehouse_id, qty) as qty_by_wh
    from destination_stock
    group by product_id
)
select row_number() over ()                                               as num,
       coalesce(aggs.product_id, aggd.product_id)                         as product_id,
       pci.product_barcode                                                as product_barcode,
       pci.product_name                                                   as product_name,
       pci.uom_name                                                       as uom_name,
       aggs.qty_by_wh                                                     as source_qty_by_wh,
       aggd.qty_by_wh                                                     as destination_qty_by_wh,
       split_part(pci.complete_name, ' / ', 1)                            as brand,
       split_part(pci.complete_name, ' / ', 2)                            as product_group,
       split_part(pci.complete_name, ' / ', 3)                            as product_line,
       split_part(pci.complete_name, ' / ', 4)                            as texture,
       pci.season                                                         as season,
       pci.gender                                                         as gender,
       pci.color                                                          as color,
       pci.size                                                           as size,
       pci.label                                                          as label,
       ''                                                                 as total_pending
from agg_source_stock aggs
     full join agg_destination_stock aggd on aggs.product_id = aggd.product_id
     left join product_cate_info pci on pci.product_id = coalesce(aggs.product_id, aggd.product_id)
order by num
            """
        return query

    def get_warehouse_data(self, warehouse_ids):
        data = warehouse_ids.mapped('loc_province_id') if self.report_by == 'area' else warehouse_ids
        wh_ids = []
        warehouse_names = []
        warehouse_name_by_id = {}
        for wh in data:
            wh_ids.append(str(wh['id']))
            warehouse_names.append(wh['name'])
            warehouse_name_by_id[str(wh['id'])] = wh['name']
        return dict(
            warehouse_name_by_id=warehouse_name_by_id,
            warehouse_names=warehouse_names,
            warehouse_ids=wh_ids
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

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        product_ids = self.env['product.product'].search(safe_eval(self.product_domain)).ids or [-1]
        wh_domain = [('company_id', 'in', allowed_company)]
        if self.report_by == 'area':
            wh_domain += [('loc_province_id', '!=', False)] if self.all_areas else ([('loc_province_id', 'in', self.area_ids.ids)] if self.area_ids else [('loc_province_id', '=', False)])
        else:
            wh_domain += safe_eval(self.warehouse_domain)
        warehouse_ids = self.env['stock.warehouse'].search(wh_domain)
        wh_ids = warehouse_ids.ids or [-1]
        query = self._get_query(product_ids, wh_ids, allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        data = self.format_data(data)
        warehouse_data = self.get_warehouse_data(warehouse_ids)
        values.update({
            'titles': TITLES + warehouse_data['warehouse_names'],
            "data": data,
            **warehouse_data
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tồn kho')
        columns = COLUMN_WIDTHS + [20] * len(data['warehouse_names'])
        sheet.set_row(0, 25)
        report_by = 'khu vực' if self.report_by == 'area' else 'chi nhánh'
        sheet.write(0, 0, 'Báo cáo tồn kho theo %s' % report_by, formats.get('header_format'))
        sheet.write(2, 0, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES + data['warehouse_names']):
            sheet.write(4, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, columns[idx])
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('brand'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('product_group'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('product_line'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('texture'), formats.get('normal_format'))
            sheet.write(row, 5, ', '.join(value.get('season') or []), formats.get('normal_format'))
            sheet.write(row, 6, ', '.join(value.get('gender') or []), formats.get('normal_format'))
            sheet.write(row, 7, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('uom_name'), formats.get('normal_format'))
            sheet.write(row, 10, ', '.join(value.get('color') or []), formats.get('normal_format'))
            sheet.write(row, 11, ', '.join(value.get('size') or []), formats.get('normal_format'))
            sheet.write(row, 12, ', '.join(value.get('label') or []), formats.get('normal_format'))
            sheet.write(row, 13, value.get('total_qty'), formats.get('float_number_format'))
            sheet.write(row, 14, value.get('total_pending'), formats.get('float_number_format'))
            col = 15
            for i in data['warehouse_ids']:
                sheet.write(row, col, value.get('product_qty_by_warehouse', {}).get(i), formats.get('float_number_format'))
                col += 1
            row += 1
