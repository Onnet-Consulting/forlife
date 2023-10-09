# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Số PR', 'Ngày PR', 'Người mua hàng', 'Mã vụ việc', 'Số PO', 'Ngày PO', 'NCC', 'Loại nhóm sản phẩm', 'Mã SKU', 'Barcode', 'Tên hàng',
    'SL', 'Đơn giá', 'CK (%)', 'Thành tiền', 'SL nhập kho', 'SL chưa nhập kho', 'SL lên hóa đơn'
]
# '% thuế nội địa', 'Tổng tiền thuế nội địa', '% Thuế nhập khẩu', 'Thuế nhập khẩu', '% Thuế tiêu thụ đặc biệt',
#     'Thuế tiêu thụ đặc biệt', '% Thuế GTGT', 'Thuế GTGT', 'Tổng tiền thuế',


class ReportNum13(models.TransientModel):
    _name = 'report.num13'
    _inherit = ['report.base', 'report.category.type']
    _description = 'Báo cáo tình hình thực hiện đơn hàng mua'

    from_date = fields.Date('From date')
    to_date = fields.Date('To date')
    po_number = fields.Char(string='PO number')
    product_ids = fields.Many2many('product.product', 'report_num13_product_rel', string='Products')
    product_group_ids = fields.Many2many('product.category', 'report_num13_group_rel', string='Level 2')
    product_line_ids = fields.Many2many('product.category', 'report_num13_line_rel', string='Level 3')
    texture_ids = fields.Many2many('product.category', 'report_num13_texture_rel', string='Level 4')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('product_brand_id')
    def onchange_product_brand(self):
        self.product_group_ids = self.product_group_ids.filtered(lambda f: f.parent_id.id in self.product_brand_id.ids)

    @api.onchange('product_group_ids')
    def onchange_product_group(self):
        self.product_line_ids = self.product_line_ids.filtered(lambda f: f.parent_id.id in self.product_group_ids.ids)

    @api.onchange('product_line_ids')
    def onchange_product_line(self):
        self.texture_ids = self.texture_ids.filtered(lambda f: f.parent_id.id in self.product_line_ids.ids)

    def _get_query(self, allowed_company, product_ids):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        po_number_list = [x.strip() for x in self.po_number.split(',') if x] if self.po_number else []
        po_number_condition = f"and po.name = any (array{po_number_list})" if po_number_list else ''

        sql = f"""
with data_pol as (select pol.id         as pol_id,
                         pol.product_id as product_id,
                         po.id          as po_id
                  from purchase_order_line pol
                           join purchase_order po on pol.order_id = po.id
                  where pol.company_id = any(array{allowed_company})
                  {f"and {format_date_query('po.date_order', tz_offset)} between '{self.from_date}' and '{self.to_date}'" if not self.po_number else ''}
                  {f'and pol.product_id = any(array{product_ids})' if product_ids else ''}
                  {po_number_condition}),
     cates as (select distinct pt.categ_id
               from product_product pp
                        join product_template pt on pp.product_tmpl_id = pt.id
                            {f"and pp.id = any(array{product_ids})" if product_ids else "and pp.id in (select distinct product_id from data_pol)"}),
     category_types as (with RECURSIVE find_root AS (SELECT id as root_id, id, parent_id, category_type_id
                                                     FROM product_category
                                                     WHERE id in (select id from cates)
                                                     UNION ALL
                                                     SELECT fr.root_id, pc.id, pc.parent_id, pc.category_type_id
                                                     FROM product_category pc
                                                              JOIN find_root fr ON pc.id = fr.parent_id)
                        select json_object_agg(fr.root_id, pct.name) as data
                        from find_root fr
                                 left join product_category_type pct on pct.id = fr.category_type_id
                        where parent_id isnull),
     pr_info as (select po_id,
                        array_to_string(array_agg(pr_name), ', ') as pr_name,
                        array_to_string(array_agg(pr_date), ', ') as pr_date
                 from (select poprr.purchase_order_id                                  as po_id,
                              pr.name                                                  as pr_name,
                              to_char(pr.request_date + '7 h'::interval, 'DD/MM/YYYY') as pr_date
                       from purchase_order_purchase_request_rel poprr
                                join purchase_request pr on poprr.purchase_request_id = pr.id
                       where poprr.purchase_order_id in (select distinct po_id from data_pol)) as x
                 group by po_id),
     pr_info_final as (select json_object_agg(po_id, pr_name) as pr_names,
                              json_object_agg(po_id, pr_date) as pr_dates
                       from pr_info)              
select row_number() over (order by po.date_order desc)                      as num,
    (select pr_names::json -> po.id::text from pr_info_final)               as pr_name,
    (select pr_dates::json -> po.id::text from pr_info_final)               as pr_date,
    po.name                                                                 as po_name,
    rp1.name                                                                as nguoi_mua,
    oc.name                                                                 as ma_vu_viec,
    to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY')        as po_date,
    rp.name                                                                 as suppliers_name,
    (select data::json ->> pt.categ_id::text from category_types)           as category_type,
    pt.sku_code                                                             as sku_code,
    pp.barcode                                                              as barcode,
    coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US') as product_name,
    pol.product_qty,
    pol.price_unit,
    pol.discount_percent,
    pol.price_subtotal,
    pol.qty_received,
    pol.product_qty - pol.qty_received                                      as qty_not_received,
    pol.qty_invoiced
from purchase_order_line pol
    join purchase_order po on pol.order_id = po.id
    left join res_partner rp on rp.id = po.partner_id
    left join res_users ru on ru.id = po.user_id
    left join res_partner rp1 on rp1.id = ru.partner_id
    left join product_product pp on pp.id = pol.product_id
    left join product_template pt on pt.id = pp.product_tmpl_id
    left join occasion_code oc on oc.id = pol.occasion_code_id
where pol.id in (select distinct pol_id from data_pol)    
order by num
"""
        return sql

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Product = self.env['product.product'].with_context(report_ctx='report.num13,product.product')
        Utility = self.env['res.utility']
        categ_ids = self.texture_ids or self.product_line_ids or self.product_group_ids or self.product_brand_id
        if self.product_ids:
            product_ids = self.product_ids.ids
        elif categ_ids:
            product_ids = Product.search([('categ_id', 'in', Utility.get_all_category_last_level(categ_ids))]).ids or [-1]
        else:
            product_ids = []
        query = self._get_query(allowed_company, product_ids)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tình hình thực hiện đơn hàng mua')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo tình hình thực hiện đơn hàng mua', formats.get('header_format'))
        if self.from_date and self.to_date:
            sheet.write(2, 0, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
            sheet.write(2, 2, 'Số YC: %s' % (self.po_number or ''), formats.get('italic_format'))
        else:
            sheet.write(2, 0, 'Số YC: %s' % (self.po_number or ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('pr_name'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('pr_date'), formats.get('center_format'))
            sheet.write(row, 3, value.get('nguoi_mua'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ma_vu_viec'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('po_name'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('po_date'), formats.get('center_format'))
            sheet.write(row, 7, value.get('suppliers_name'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('category_type'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('sku_code'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('barcode'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('product_qty', 0), formats.get('float_number_format'))
            sheet.write(row, 13, value.get('price_unit', 0), formats.get('int_number_format'))
            sheet.write(row, 14, value.get('discount_percent', 0), formats.get('float_number_format'))
            sheet.write(row, 15, value.get('price_subtotal', 0), formats.get('int_number_format'))
            sheet.write(row, 16, value.get('qty_received', 0), formats.get('float_number_format'))
            sheet.write(row, 17, value.get('qty_not_received', 0), formats.get('float_number_format'))
            sheet.write(row, 18, value.get('qty_invoiced', 0), formats.get('float_number_format'))
            row += 1
