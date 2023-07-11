# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.tools.safe_eval import safe_eval

TITLES = ['STT', 'Mã Hàng', 'Tên Hàng', 'Nhóm hàng', 'Màu', 'Size', 'Bộ sưu tập', 'Kết cấu', 'Dòng hàng', 'SL cuối kỳ']
COLUMN_WIDTHS = [8, 20, 30, 20, 15, 10, 30, 20, 20, 20]


class ReportNum4(models.TransientModel):
    _name = 'report.num4'
    _inherit = 'report.base'
    _description = 'Report stock by product'

    to_date = fields.Date(string='To date', required=True, default=fields.Date.context_today)
    product_domain = fields.Char('Product', default='[]')
    warehouse_domain = fields.Char('Warehouse', default='[]')

    def _get_query(self, product_ids, warehouse_ids, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        attr_value = self.env['res.utility'].get_attribute_code_config()

        where_query = f"""
            sm.company_id = any (array{allowed_company})
            and sm.state = 'done'
            and sm.product_id = any (array{product_ids})
            and {format_date_query("sm.date", tz_offset)} <= '{str(self.to_date)}'
            and (src_wh.id = any (array{warehouse_ids}) or des_wh.id = any (array{warehouse_ids}))
        """

        query = f"""
with attribute_data as (
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
product_cate_info as
    (select 
        pp.id     		                                                          as product_id,
        cate.complete_name                                                        as complete_name,
        pp.barcode                                                                as product_barcode,
        coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')   as product_name,
        pt.collection                                                             as collection,
        ad.attrs::json ->> '{attr_value.get('size', '')}'                          as size,
        ad.attrs::json ->> '{attr_value.get('mau_sac', '')}'                       as color
    from product_product pp 
        left join product_template pt on pt.id = pp.product_tmpl_id
        join product_category cate on cate.id = pt.categ_id
        left join attribute_data ad on ad.product_id = pp.id
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
    where {where_query}
    group by sm.product_id
    )
select row_number() over ()                     as num,
       pci.product_barcode                      as product_barcode,
       pci.product_name                         as product_name,
       split_part(pci.complete_name, ' / ', 2)  as product_group,
       split_part(pci.complete_name, ' / ', 3)  as product_line,
       split_part(pci.complete_name, ' / ', 4)  as texture,
       pci.collection                           as collection,
       pci.color                                as color,
       pci.size                                 as size,
       stock.qty                                as total_qty
from stock
    left join product_cate_info pci on pci.product_id = stock.product_id
order by num
            """
        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        product_ids = self.env['product.product'].search(safe_eval(self.product_domain)).ids or [-1]
        warehouse_ids = self.env['stock.warehouse'].search(safe_eval(self.warehouse_domain) + [('company_id', 'in', allowed_company)]).ids or [-1]
        query = self._get_query(product_ids, warehouse_ids, allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tồn kho')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo tồn kho theo sản phẩm', formats.get('header_format'))
        sheet.write(2, 0, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, COLUMN_WIDTHS[idx])
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('product_group'), formats.get('normal_format'))
            sheet.write(row, 4, ', '.join(value.get('color') or []), formats.get('normal_format'))
            sheet.write(row, 5, ', '.join(value.get('size') or []), formats.get('normal_format'))
            sheet.write(row, 6, value.get('collection'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('texture'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('product_line'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('total_qty'), formats.get('float_number_format'))
            row += 1
