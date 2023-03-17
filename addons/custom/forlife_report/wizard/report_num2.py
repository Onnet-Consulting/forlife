# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

TITLES = ['Mã SP', 'Tên SP', 'Size', 'Màu', 'Tồn', 'Giá niêm yết', 'Giá khuyến mãi']
COLUMN_WIDTHS = [20, 30, 20, 20, 20, 25, 25]


class ReportNum2(models.TransientModel):
    _name = 'report.num2'
    _inherit = 'report.base'
    _description = 'Report stock with sale price by warehouse'

    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    product_ids = fields.Many2many('product.product', string='Products', domain=[('type', '=', 'product')])
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    product_brand_ids = fields.Many2many('product.category', 'num2_product_brand_rel', 'num2_id', 'brand_id', string='Brand', domain="[('parent_id', '=', False)]")
    product_group_ids = fields.Many2many('product.category', 'num2_product_group_rel', 'num2_id', 'product_group_id', string='Product Group')
    product_line_ids = fields.Many2many('product.category', 'num2_product_line_rel', 'num2_id', 'product_line_id', string='Product Line')
    product_texture_ids = fields.Many2many('product.category', 'num2_product_texture_rel', 'num2_id', 'product_texture_id', string='Product Texture')

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
        action = self.env.ref('forlife_report.report_num_2_client_action').read()[0]
        return action

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang

        where_query = "sqt.company_id = %s and sw.id is not null\n"
        if not self.all_warehouses and self.warehouse_ids:
            location_conditions = ["sl.parent_path like %s"] * len(self.warehouse_ids)
            location_conditions = ' or '.join(location_conditions)
            where_query += f" and ({location_conditions})\n"
        if not self.all_products and self.warehouse_ids:
            product_conditions = "sqt.product_id = any (%s)"
            where_query += f" and {product_conditions}\n"

        query = f"""
with stock_product as
         (select sqt.product_id    as product_id,
                 sw.id             as warehouse_id,
                 ''                as product_size,
                 ''                as product_color,
                 sum(sqt.quantity) as quantity,
                 ''                as list_price,
                 ''                as discount_price

          from stock_quant sqt
                   left join product_product pp on sqt.product_id = pp.id
                   left join stock_location sl on sqt.location_id = sl.id
                   left join stock_warehouse sw
                             on sl.parent_path like concat('%%/', sw.view_location_id, '/%%')
          where {where_query}
          group by sqt.product_id,
                   product_size,
                   product_color,
                   list_price,
                   discount_price,
                   sw.id
         )
select pp.id                                                                   as product_id,
       pp.barcode                                                              as product_barcode,
       coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US') as product_name,
       sw.id                                                                   as warehouse_id,
       sw.name                                                                 as warehouse_name,
       stp.quantity                                                            as quantity
from stock_product stp
         left join product_product pp on pp.id = stp.product_id
         left join product_template pt on pp.product_tmpl_id = pt.id
         left join stock_warehouse sw on sw.id = stp.warehouse_id
        """

        return query

    def _get_query_params(self):
        self.ensure_one()
        params = [self.company_id.id]
        if not self.all_warehouses and self.warehouse_ids:
            params.extend(
                [f'%/{view_location_id}/%' for view_location_id in self.warehouse_ids.mapped('view_location_id').ids])

        if not self.all_products and self.product_ids:
            params.append(self.product_ids.ids)
        return params

    def get_data(self):
        self.ensure_one()
        query = self._get_query()
        params = self._get_query_params()
        self._cr.execute(query, params)
        data = self._cr.dictfetchall()
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
        return {
            'titles': TITLES,
            "data": list(data_by_product_id.values()),
            "detail_data_by_product_id": detail_data_by_product_id
        }

    def generate_xlsx_report(self, workbook):
        data = self.get_data()
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet(self._description)
        sheet.set_row(0, 25)
        sheet.write(0, 0, self._description, formats.get('header_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(2, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, COLUMN_WIDTHS[idx])
        row = 3
        for value in data['data']:
            sheet.write(row, 0, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 1, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('product_size'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('product_color'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('quantity'), formats.get('center_format'))
            sheet.write(row, 5, value.get('list_price'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('discount_price'), formats.get('normal_format'))
            row += 1
