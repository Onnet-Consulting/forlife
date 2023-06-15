# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.tools.safe_eval import safe_eval

TITLES = [
    'STT', 'Kho', 'Mã SP', 'Tên SP', 'Size', 'Màu', 'Đơn vị', 'Giá', 'Số lượng',
    'Chiết khấu', 'Thành tiền', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu', 'Mã loại SP', 'Kênh bán',
]

COLUMN_WIDTHS = [5, 20, 20, 30, 15, 15, 10, 20, 8, 20, 25, 20, 20, 20, 20, 20]


class ReportNum1(models.TransientModel):
    _name = 'report.num1'
    _inherit = 'report.base'
    _description = 'Report revenue by product'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    product_domain = fields.Char('Product', default='["&", ("voucher", "=", False), "|", ("detailed_type", "=", "product"), ("detailed_type", "=", "service")]')
    warehouse_domain = fields.Char('Warehouse', default='[]')
    # fixme: ('wholesale', 'Bán buôn'), ('ecom', 'Bán Online'), ('company', 'Bán liên công ty')],
    picking_type = fields.Selection([('all', 'Tất cả'), ('retail', 'Bán lẻ')],
                                    'Picking type', required=True, default='all')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self, product_ids, warehouse_ids, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        attr_value = self.env['res.utility'].get_attribute_code_config()

        query = []
        product_condition = f'and pol.product_id = any (array{product_ids})'
        warehouse_condition = f'and wh.id = any (array{warehouse_ids})'

        if self.picking_type in ('all', 'retail'):
            query.append(f"""
select
    pol.product_id                                                    as product_id,
    wh.code                                                           as warehouse,
    pol.original_price                                                as original_price,
    sum(pol.qty)::float                                               as qty,
    sum(case when disc.type = 'point' then disc.recipe * 1000
            when disc.type = 'card' then disc.recipe
            when disc.type = 'ctkm' then disc.discounted_amount
            else 0
        end 
      + (pol.original_price * pol.qty) * pol.discount / 100.0)::float as discount,
    sum(pol.qty * pol.original_price)::float                          as total_amount,
    'Bán lẻ'                                                          as sale_channel
from pos_order_line pol
    left join pos_order po on pol.order_id = po.id
    left join pos_session ps on ps.id = po.session_id
    left join pos_config pc on ps.config_id = pc.id
    left join store on store.id = pc.store_id
    left join stock_warehouse wh on wh.id = store.warehouse_id
    left join pos_order_line_discount_details disc on disc.pos_order_line_id = pol.id
where po.company_id = any(array{allowed_company}) and po.state in ('paid', 'done', 'invoiced')
    and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
    {product_condition} 
    {warehouse_condition}
group by product_id, warehouse, sale_channel, original_price
having sum(pol.qty) > 0
""")

#         if self.picking_type in ('all', 'wholesale'):
#             query.append(f"""
# select
#     ''                                                               as warehouse,
#     pp.barcode                                                       as product_barcode,
#     (select product_name from product_data_by_id where id = pp.id)   as product_name,
#     ''                                                               as product_size,
#     ''                                                               as product_color,
#     (select name from uom_name_by_id where id = aml.product_uom_id)  as uom_name,
#     aml.price_unit                                                   as price_unit,
#     sum(aml.quantity)                                                as qty,
#     sum((aml.price_unit * aml.quantity) * aml.discount / 100.0)      as discount,
#     sum(aml.price_subtotal)                                          as total_amount,
#     split_part(cate.complete_name, ' / ', 2)                         as product_group,
#     split_part(cate.complete_name, ' / ', 3)                         as product_line,
#     split_part(cate.complete_name, ' / ', 4)                         as texture_name,
#     (select account_code from account_by_categ_id where cate_id = (
#         select categ_id from product_data_by_id where id = pp.id))   as product_type_code,
#     ''                                                               as sale_channel
# from account_move_line aml
#     left join product_product pp on aml.product_id = pp.id
#     left join account_move am on aml.move_id = am.id
#     left join product_category cate on cate.id = (select categ_id from product_data_by_id where id = pp.id)
#     join sale_order_line_invoice_rel sol_rel on aml.id = sol_rel.invoice_line_id
# where am.state = 'posted'
#     and {format_date_query("am.invoice_date", tz_offset)} >= '{self.from_date}' --fixme: thay ngày hóa đơn (invoice_date) bằng ngày hạch toán (chưa có)
#     and {format_date_query("am.invoice_date", tz_offset)} <= '{self.to_date}'
#     {product_condition}
# group by
#     warehouse, product_barcode, product_name, product_size, product_color, uom_name,
#     price_unit, product_group, product_line, texture_name, product_type_code, sale_channel
# having sum(aml.quantity) > 0
# """)
#
#         if self.picking_type in ('all', 'ecom'):
#             pass

        final_query = f"""
WITH account_by_categ_id as ( -- lấy mã tài khoản định giá tồn kho bằng cate_id
    select 
        cate.id as cate_id,
        aa.code as account_code
    from product_category cate
        left join ir_property ir on ir.res_id = concat('product.category,', cate.id)
        left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
    where  ir.name='property_stock_valuation_account_id' and ir.company_id = any(array{allowed_company})
    order by cate.id 
),
attribute_data as (
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
product_data_by_id as ( -- lấy các thông tin của sản phẩm bằng product.product ID
    select 
        pp.id,
        pp.barcode as product_barcode,
        pt.product_name,
        pt.categ_id,
        pt.uom_name,
        pt.cate_name,
        ad_size.value as size,
        ad_color.value as color
    from product_product pp
        left join (select
                    id, categ_id, cate_name,
                    substr(product_name, 2, length(product_name)-2) as product_name,
                    substr(uom_name, 2, length(uom_name)-2) as uom_name
                   from (select 
                            pt1.id,
                            pt1.categ_id,
                            pc.complete_name as cate_name,
                            coalesce(pt1.name::json -> '{user_lang_code}', pt1.name::json -> 'en_US')::text as product_name,
                            coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US')::text as uom_name
                         from product_template pt1
                            left join uom_uom uom on uom.id = pt1.uom_id
                            left join product_category pc on pc.id = pt1.categ_id
                        ) as subname_table
                ) as pt
        on pt.id = pp.product_tmpl_id
        left join attribute_data ad_size on ad_size.product_id = pp.id and ad_size.attrs_code = '{attr_value.get('size', '')}'
        left join attribute_data ad_color on ad_color.product_id = pp.id and ad_color.attrs_code = '{attr_value.get('mau_sac', '')}'
    where pp.id = any (array{product_ids})
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
    res.warehouse                             as warehouse,
    p_data.product_barcode                    as product_barcode,
    p_data.product_name                       as product_name,
    p_data.size                               as product_size,
    p_data.color                              as product_color,
    p_data.uom_name                           as uom_name,
    res.original_price                        as price_unit,
    res.qty                                   as qty,
    coalesce(res.discount, 0)                 as discount,
    coalesce(res.total_amount, 0)             as total_amount,
    split_part(p_data.cate_name, ' / ', 2)    as product_group,
    split_part(p_data.cate_name, ' / ', 3)    as product_line,
    split_part(p_data.cate_name, ' / ', 4)    as texture_name,
    acc.account_code                          as product_type_code,
    res.sale_channel                          as sale_channel
from result_table res
    left join product_data_by_id p_data on p_data.id = res.product_id
    left join account_by_categ_id acc on acc.cate_id = p_data.categ_id
order by num
                """
        return final_query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        product_ids = self.env['product.product'].search(safe_eval(self.product_domain)).ids or [-1]
        warehouse_ids = self.env['stock.warehouse'].search(safe_eval(self.warehouse_domain) + [('company_id', 'in', allowed_company)]).ids or [-1]
        query = self._get_query(product_ids, warehouse_ids, allowed_company)
        data = self.execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            'data': data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        p_type = {
            'all': 'Tất cả',
            'retail': 'Bán lẻ',
            'wholesale': 'Bán buôn',
            'ecom': 'Bán Online',
            'company': 'Bán liên công ty',
        }
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo doanh thu theo sản phẩm')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo doanh thu theo sản phẩm', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày: %s' % self.from_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 2, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 4, 'Loại phiếu: %s' % p_type.get(self.picking_type, ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, COLUMN_WIDTHS[idx])
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('warehouse'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 4, ', '.join(value.get('product_size') or []), formats.get('normal_format'))
            sheet.write(row, 5, ', '.join(value.get('product_color') or []), formats.get('normal_format'))
            sheet.write(row, 6, value.get('uom_name'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('price_unit'), formats.get('float_number_format'))
            sheet.write(row, 8, value.get('qty'), formats.get('center_format'))
            sheet.write(row, 9, value.get('discount'), formats.get('float_number_format'))
            sheet.write(row, 10, value.get('total_amount', 0) - value.get('discount', 0), formats.get('float_number_format'))
            sheet.write(row, 11, value.get('product_group'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('product_line'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('texture_name'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('product_type_code'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('sale_channel'), formats.get('normal_format'))
            row += 1
