# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval

TITLES = ['Mã SP', 'Tên SP', 'Size', 'Màu', 'Tồn', 'Giá niêm yết', 'Giá khuyến mãi']
COLUMN_WIDTHS = [20, 30, 20, 20, 20, 25, 25]


class ReportNum2(models.TransientModel):
    _name = 'report.num2'
    _inherit = 'report.base'
    _description = 'Report stock with sale price by warehouse'

    product_domain = fields.Char('Product', default='[]')
    warehouse_domain = fields.Char('Warehouse', default='[]')

    def _get_query(self, product_ids, warehouse_ids, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        user_lang_code = self.env.user.lang
        attr_value = self.env['res.utility'].get_attribute_code_config()

        where_query = f"sqt.company_id = any (array{allowed_company}) and sw.id notnull\n"
        if warehouse_ids:
            location_conditions = ' or '.join([f"sl.parent_path like '%%/{view_location_id}/%%'" for view_location_id in warehouse_ids.mapped('view_location_id').ids])
            where_query += f" and ({location_conditions})\n"
        if product_ids:
            where_query += f" and sqt.product_id = any (array{product_ids})\n"

        query = f"""
with attribute_data as (
    select 
        pp.id                                                                                   as product_id,
        pa.attrs_code                                                                           as attrs_code,
        array_agg(coalesce(pav.name::json -> '{user_lang_code}', pav.name::json -> 'en_US'))    as value
    from product_template_attribute_line ptal
    left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
    left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
    left join product_attribute pa on ptal.attribute_id = pa.id
    left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
    where pp.id = any (array{product_ids}) 
    group by pp.id, pa.attrs_code
), 
stock_product as (
    select
        sqt.product_id    as product_id,
        sw.id             as warehouse_id,
        sum(sqt.quantity) as quantity
    from stock_quant sqt
        left join product_product pp on sqt.product_id = pp.id
        left join stock_location sl on sqt.location_id = sl.id
        left join stock_warehouse sw on sl.parent_path like concat('%%/', sw.view_location_id, '/%%')
    where {where_query}
    group by sqt.product_id, sw.id
)
select  pp.id                                                                   as product_id,
        pp.barcode                                                              as product_barcode,
        coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US') as product_name,
        sw.id                                                                   as warehouse_id,
        sw.name                                                                 as warehouse_name,
        stp.quantity                                                            as quantity,
        ad_size.value                                                           as product_size,
        ad_color.value                                                          as product_color,
        pt.list_price                                                           as list_price,
        ''                                                                      as discount_price
from stock_product stp
    left join product_product pp on pp.id = stp.product_id
    left join product_template pt on pp.product_tmpl_id = pt.id
    left join stock_warehouse sw on sw.id = stp.warehouse_id
    left join attribute_data ad_size on ad_size.product_id = stp.product_id and ad_size.attrs_code = '{attr_value.get('size', '')}'
    left join attribute_data ad_color on ad_color.product_id = stp.product_id and ad_color.attrs_code = '{attr_value.get('mau_sac', '')}'
"""

        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        product_ids = self.env['product.product'].search(safe_eval(self.product_domain)).ids or [-1]
        warehouse_ids = self.env['stock.warehouse'].search(safe_eval(self.warehouse_domain) + [('company_id', 'in', allowed_company)])
        query = self._get_query(product_ids, warehouse_ids, allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        data_by_product_id = {}
        detail_data_by_product_id = {}
        for line in data:
            product_id = line.get('product_id')
            if product_id not in data_by_product_id:
                data_by_product_id[product_id] = line
            else:
                data_by_product_id[product_id]['quantity'] += line['quantity']

            detail_data = {
                "warehouse_name": line.get('warehouse_name'),
                "quantity": line.get("quantity")
            }
            if product_id not in detail_data_by_product_id:
                detail_data_by_product_id[product_id] = [detail_data]
            else:
                detail_data_by_product_id[product_id].append(detail_data)
        values.update({
            'titles': TITLES,
            "data": list(data_by_product_id.values()),
            "detail_data_by_product_id": detail_data_by_product_id,
            "recordPerPage": 25,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tồn kho - giá bán')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo tồn kho - giá bán', formats.get('header_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(2, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, COLUMN_WIDTHS[idx])
        row = 3
        for value in data['data']:
            sheet.write(row, 0, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 1, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 2, ', '.join(value.get('product_size') or []), formats.get('normal_format'))
            sheet.write(row, 3, ', '.join(value.get('product_color') or []), formats.get('normal_format'))
            sheet.write(row, 4, value.get('quantity'), formats.get('center_format'))
            sheet.write(row, 5, value.get('list_price'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('discount_price'), formats.get('normal_format'))
            row += 1
