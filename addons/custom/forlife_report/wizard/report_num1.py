# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

PICKING_TYPE = [
    ('all', 'Tất cả'),
    ('retail', 'Bán lẻ'),
    ('wholesale', 'Bán buôn'),
    ('ecom', 'Bán Online')
]

TITLES = [
    'STT',
    'Kho',
    'Mã SP',
    'Tên SP',
    'Size',
    'Màu',
    'Đơn vị',
    'Giá',
    'Số lượng',
    'Chiết khấu',
    'Thành tiền',
    'Nhóm hàng',
    'Dòng hàng',
    'Kết cấu',
    'Mã loại SP',
    'Kênh bán',
]

COLUMN_WIDTHS = [5, 20, 20, 30, 15, 15, 10, 20, 8, 20, 25, 20, 20, 20, 20, 20]


class ReportNum1(models.TransientModel):
    _name = 'report.num1'
    _inherit = 'report.base'
    _description = 'Report revenue by product'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    product_ids = fields.Many2many('product.product', string='Products')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    picking_type = fields.Selection(PICKING_TYPE, 'Picking type', required=True, default='all')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self, product_ids, warehouse_ids):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        query = []
        product_condition = 'and pp.id in (%s)' % ','.join(map(str, product_ids)) if product_ids else ''
        warehouse_condition = 'and wh.id in (%s)' % ','.join(map(str, warehouse_ids)) if warehouse_ids else ''
        if self.picking_type in ('all', 'retail'):
            query.append(f"""
select
    wh.code                                                           as warehouse,
    pp.barcode                                                        as product_barcode,
    (select product_name from product_data_by_id where id = pp.id)    as product_name,
    ''                                                                as product_size,
    ''                                                                as product_color,
    (select uom_name from product_data_by_id where id = pp.id)        as uom_name,
    pol.price_unit                                                    as price_unit,
    sum(pol.qty)                                                      as qty,
    sum((pol.price_unit * pol.qty) * pol.discount / 100.0)            as discount,
    sum(pol.price_subtotal_incl)                                      as amount_with_tax,
    split_part(cate.complete_name, ' / ', 2)                          as product_group,
    split_part(cate.complete_name, ' / ', 3)                          as product_line,
    split_part(cate.complete_name, ' / ', 4)                          as texture_name,
    (select account_code from account_by_categ_id where cate_id = (
        select categ_id from product_data_by_id where id = pp.id))    as product_type_code,
    ''                                                                as sale_channel
from pos_order_line pol
    left join product_product pp on pol.product_id = pp.id
    left join pos_order po on pol.order_id = po.id
    left join pos_session ps on ps.id = po.session_id
    left join pos_config pc on ps.config_id = pc.id
    left join store on store.id = pc.store_id
    left join stock_warehouse wh on wh.id = store.warehouse_id
    left join product_category cate on cate.id = (select categ_id from product_data_by_id where id = pp.id)
where po.company_id = {self.company_id.id}
    and po.state in ('paid', 'done', 'invoiced')
    and {format_date_query("po.date_order", tz_offset)} >= '{self.from_date}'
    and {format_date_query("po.date_order", tz_offset)} <= '{self.to_date}'
    {product_condition} 
    {warehouse_condition}
group by 
    warehouse, product_barcode, product_name, product_size, product_color, uom_name,
    price_unit, product_group, product_line, texture_name, product_type_code, sale_channel
having sum(pol.qty) > 0
                """)
        if self.picking_type in ('all', 'wholesale'):
            query.append(f"""
select
    ''                                                               as warehouse,
    pp.barcode                                                       as product_barcode,
    (select product_name from product_data_by_id where id = pp.id)   as product_name,
    ''                                                               as product_size,
    ''                                                               as product_color,
    (select name from uom_name_by_id where id = aml.product_uom_id)  as uom_name,
    aml.price_unit                                                   as price_unit,
    sum(aml.quantity)                                                as qty,
    sum((aml.price_unit * aml.quantity) * aml.discount / 100.0)      as discount,
    sum(aml.price_subtotal)                                          as amount_with_tax,
    split_part(cate.complete_name, ' / ', 2)                         as product_group,
    split_part(cate.complete_name, ' / ', 3)                         as product_line,
    split_part(cate.complete_name, ' / ', 4)                         as texture_name,
    (select account_code from account_by_categ_id where cate_id = (
        select categ_id from product_data_by_id where id = pp.id))   as product_type_code,
    ''                                                               as sale_channel
from account_move_line aml
    left join product_product pp on aml.product_id = pp.id
    left join account_move am on aml.move_id = am.id
    left join product_category cate on cate.id = (select categ_id from product_data_by_id where id = pp.id)
    join sale_order_line_invoice_rel sol_rel on aml.id = sol_rel.invoice_line_id
where am.state = 'posted'
    and {format_date_query("am.invoice_date", tz_offset)} >= '{self.from_date}' --fixme: thay ngày hóa đơn (invoice_date) bằng ngày hạch toán (chưa có)
    and {format_date_query("am.invoice_date", tz_offset)} <= '{self.to_date}'
    {product_condition}
group by 
    warehouse, product_barcode, product_name, product_size, product_color, uom_name,
    price_unit, product_group, product_line, texture_name, product_type_code, sale_channel
having sum(aml.quantity) > 0
                """)
        if self.picking_type in ('all', 'ecom'):
            pass

        final_query = f"""
WITH account_by_categ_id as ( -- lấy mã tài khoản định giá tồn kho bằng cate_id
    select 
        cate.id as cate_id,
        aa.code as account_code
    from product_category cate
        left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
        left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
    where  ir.name='property_stock_valuation_account_id' and ir.company_id = {self.company_id.id}
    order by cate.id 
),
product_data_by_id as ( -- lấy tên sản phẩm đã convert, đơn vị tính đã conver, categ_id bằng product.product ID
    select 
        pp.id,
        pt.product_name,
        pt.categ_id,
        pt.uom_name
    from product_product pp
        left join (select
                    id,
                    substr(product_name, 2, length(product_name)-2) as product_name,
                    categ_id,
                    substr(uom_name, 2, length(uom_name)-2) as uom_name
                   from (select 
                            pt1.id,
                            coalesce(pt1.name::json -> '{user_lang_code}', pt1.name::json -> 'en_US')::text as product_name,
                            pt1.categ_id,
                            coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US')::text as uom_name
                         from product_template pt1
                            left join uom_uom uom on uom.id = pt1.uom_id) as subname_table) as pt
        on pt.id = pp.product_tmpl_id
    order by pp.product_tmpl_id asc
),
uom_name_by_id as ( -- lấy tên đơn vị tính đã convert bằng ID
    select 
        id,
        substr(name, 2, length(name)-2) as name
    from (select
            id,
            coalesce(name::json -> '{user_lang_code}', name::json -> 'en_US')::text as name
        from uom_uom) as tb
),
result_table as (
    {' UNION ALL '.join(query)}
)
select 
    row_number() over (order by product_name) as num,
    warehouse,
    product_barcode,
    product_name,
    product_size,
    product_color,
    uom_name,
    price_unit,
    sum(qty)                                  as qty,
    sum(discount)                             as discount,
    sum(amount_with_tax)                      as amount_with_tax,
    product_group,
    product_line,
    texture_name,
    product_type_code,
    sale_channel
from result_table
group by 
    warehouse, product_barcode, product_name, product_size, product_color, uom_name,
    price_unit, product_group, product_line, texture_name, product_type_code, sale_channel
order by product_name
                """
        return final_query

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        product_ids = (self.env['product.product'].search([('type', '=', 'product')]).ids or [-1]) if self.all_products else self.product_ids.ids
        warehouse_ids = (self.env['stock.warehouse'].search([]).ids or [-1]) if self.all_warehouses else self.warehouse_ids.ids
        query = self._get_query(product_ids, warehouse_ids)
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            'data': data,
        })
        return values

    def generate_xlsx_report(self, workbook):
        data = self.get_data()
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo doanh thu theo sản phẩm')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo doanh thu theo sản phẩm', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày: %s' % self.from_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 2, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 4, 'Loại phiếu: %s' % next((t[1] for t in self._fields.get('picking_type').selection if t[0] == self.picking_type), ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, COLUMN_WIDTHS[idx])
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('warehouse'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('product_size'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('product_color'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('uom_name'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('price_unit'), formats.get('float_number_format'))
            sheet.write(row, 8, value.get('qty'), formats.get('center_format'))
            sheet.write(row, 9, value.get('discount'), formats.get('float_number_format'))
            sheet.write(row, 10, value.get('amount_with_tax'), formats.get('float_number_format'))
            sheet.write(row, 11, value.get('product_group'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('product_line'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('texture_name'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('product_type_code'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('sale_channel'), formats.get('normal_format'))
            row += 1
