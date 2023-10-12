# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

TITLES = [
    'STT', 'Loại', 'Mã TS/CCDC', 'Tên', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu', 'Trung tâm chi phí', 'Kho/Địa điểm đặt', 'Nhân viên', 'SL tồn'
]


class ReportNum40(models.TransientModel):
    _name = 'report.num40'
    _inherit = ['report.base', 'report.category.type']
    _description = 'Báo cáo tài sản công cụ dụng cụ'

    to_date = fields.Date(string='To date', required=True)
    product_ids = fields.Many2many('product.product', 'report_num40_product_rel', string='Products')
    warehouse_ids = fields.Many2many('stock.warehouse', 'report_num40_warehouse_rel', string='Kho tính tồn')
    asset_ids = fields.Many2many('assets.assets', 'report_num40_asset_rel', string='Assets')
    location_ids = fields.Many2many('asset.location', 'report_num40_asset_location_rel', string='Địa điểm tài sản')
    category_type_id = fields.Many2one('product.category.type', default=lambda f: f.env.ref('forlife_base.product_category_type_03', raise_if_not_found=False))
    product_group_ids = fields.Many2many('product.category', 'report_num40_group_rel', string='Level 2')
    product_line_ids = fields.Many2many('product.category', 'report_num40_line_rel', string='Level 3')
    texture_ids = fields.Many2many('product.category', 'report_num40_texture_rel', string='Level 4')

    @api.onchange('product_brand_id')
    def onchange_product_brand(self):
        self.product_group_ids = self.product_group_ids.filtered(lambda f: f.parent_id.id in self.product_brand_id.ids)

    @api.onchange('product_group_ids')
    def onchange_product_group(self):
        self.product_line_ids = self.product_line_ids.filtered(lambda f: f.parent_id.id in self.product_group_ids.ids)

    @api.onchange('product_line_ids')
    def onchange_product_line(self):
        self.texture_ids = self.texture_ids.filtered(lambda f: f.parent_id.id in self.product_line_ids.ids)

    def _get_query(self, product_ids, warehouse_ids, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset

        query_final = f"""
with asset_data as (
    select x.loai,
           x.ma_ts_ccdc,
           x.ten,
           x.nhom_hang,
           x.dong_hang,
           x.ket_cau,
           x.tttp,
           x.kho,
           x.nhan_vien,
           x.sl_ton
    from (select row_number() over (PARTITION BY aa.id
        order by hat.validate_date desc, hatl.id desc) as stt,
                 'Thẻ TS/CCDC'                         as loai,
                 aa.code                               as ma_ts_ccdc,
                 aa.name                               as ten,
                 ''                                    as nhom_hang,
                 ''                                    as dong_hang,
                 ''                                    as ket_cau,
                 concat(aaa.code, ' - ', coalesce(aaa.name->>'{user_lang_code}', aaa.name->>'en_US')) as tttp,
                 al.name                               as kho,
                 he.name                               as nhan_vien,
                 aa.quantity                           as sl_ton
          from hr_asset_transfer_line hatl
                   join hr_asset_transfer hat on hatl.hr_asset_transfer_id = hat.id
                   join assets_assets aa on hatl.asset_code = aa.id
                   left join asset_location al on aa.location = al.id
                   left join hr_employee he on he.id = aa.employee
                   left join account_analytic_account aaa on aaa.id = aa.dept_code
          where (hat.validate_date + interval '{tz_offset} h')::date <= '{self.to_date}' and hat.state = 'done'
            {f'and al.id = any(array{self.location_ids.ids})' if self.location_ids else ''}
            {f'and aa.id = any(array{self.asset_ids.ids})' if self.asset_ids else ''}) as x
    where stt = 1
),
stock_move_data as (
    select xxx.product_id,
           xxx.warehouse_id,
           sum(qty) as qty
    from (select sm1.product_id as product_id,
                 sl1.warehouse_id as warehouse_id,
                 sum(-sm1.quantity_done) as qty
          from stock_move sm1
                join stock_location sl1 on sm1.location_id = sl1.id 
          where sm1.product_id = any(array{product_ids})
            and sm1.company_id  = any(array{allowed_company})
            and sm1.state = 'done'
            and sl1.warehouse_id = any(array{warehouse_ids})
          group by sm1.product_id, sl1.warehouse_id
          union all
          select sm2.product_id as product_id,
                 sl2.warehouse_id as warehouse_id,
                 sum(sm2.quantity_done) as qty
          from stock_move sm2
               join stock_location sl2 on sm2.location_dest_id = sl2.id
          where sm2.product_id = any(array{product_ids})
            and sm2.company_id  = any(array{allowed_company})
            and sm2.state = 'done'
            and sl2.warehouse_id = any(array{warehouse_ids})
          group by sm2.product_id, sl2.warehouse_id) as xxx
    group by product_id, warehouse_id
),
move_data_final as (
    select 'Lưu kho'                                                  as loai,
            pp.barcode                                                as ma_ts_ccdc,
            coalesce(pt.name->>'{user_lang_code}', pt.name->>'en_US') as ten,
            split_part(pc.complete_name, ' / ', 2)                    as nhom_hang,
            split_part(pc.complete_name, ' / ', 3)                    as dong_hang,
            split_part(pc.complete_name, ' / ', 4)                    as ket_cau,
            ''                                                        as tttp,
            wh.name                                                   as kho,
            ''                                                        as nhan_vien,
            smd.qty                                                   as sl_ton
    from stock_move_data smd
        join product_product pp on pp.id = smd.product_id
        join product_template pt on pt.id = pp.product_tmpl_id
        join product_category pc on pc.id = pt.categ_id
        join stock_warehouse wh on wh.id = smd.warehouse_id
)
select row_number() over () as stt,
       val.*
from (select * from asset_data union all select * from move_data_final) as val
order by stt
"""
        return query_final

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Product = self.env['product.product'].with_context(report_ctx='report.num40,product.product')
        Warehouse = self.env['stock.warehouse'].with_context(report_ctx='report.num40,stock.warehouse')
        Utility = self.env['res.utility']
        categ_ids = self.texture_ids or self.product_line_ids or self.product_group_ids or self.product_brand_id
        if self.product_ids:
            product_ids = self.product_ids.ids
        elif categ_ids:
            product_ids = Product.search([('categ_id', 'in', Utility.get_all_category_last_level(categ_ids))]).ids or [-1]
        else:
            product_ids = [-1]
        warehouse_ids = self.warehouse_ids.ids if self.warehouse_ids else (Warehouse.search([('company_id', 'in', allowed_company)]).ids or [-1])
        query = self._get_query(product_ids, warehouse_ids, allowed_company)
        data = Utility.execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tài sản công cụ dụng cụ')
        sheet.set_row(0, 30)
        sheet.write(0, 0, 'Báo cáo tài sản công cụ dụng cụ', formats.get('header_format'))
        sheet.write(1, 0, 'Công ty: %s' % self.env.company.name, formats.get('normal_format'))
        sheet.write(3, 0, 'Đến ngày: %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(5, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(TITLES) - 1, 20)
        row = 6
        for value in data['data']:
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('loai'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ma_ts_ccdc'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ten'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ket_cau'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('tttp'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('kho'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('nhan_vien'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('sl_ton'), formats.get('int_number_format'))
            row += 1
