# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Trạng thái', 'Số CT', 'Ngày lập phiếu', 'Ngày duyệt lỗi', 'Mã cửa hàng', 'Tên cửa hàng', 'Mã hàng', 'Tên hàng', 'Màu', 'Size', 'Số lượng yêu cầu',
    'Số lượng duyệt', 'Phần trăm GG', 'Số tiền giảm', 'Mô tả lỗi', 'Phân loại lỗi', 'Người tạo', 'Người duyệt', 'Nhóm hàng', 'Dòng hàng', 'Kết cấu'
]


class ReportNum45(models.TransientModel):
    _name = 'report.num45'
    _inherit = 'report.base'
    _description = 'Báo cáo chi tiết phiếu lỗi'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    store_ids = fields.Many2many('store', string='Store')
    state_ids = fields.Many2many('ir.model.fields.selection', 'ir_model_fields_selection_report45_rel', string='Trạng thái',
                                 domain=[('field_id.name', '=', 'state'), ('field_id.model', '=', 'product.defective')])
    product_ids = fields.Many2many('product.product', 'report_num45_product_rel', string='Products')
    defective_type_ids = fields.Many2many('defective.type', 'defective_type_report45_rel', string='Phân loại lỗi')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand_id(self):
        self.store_ids = self.store_ids.filtered(lambda f: f.brand_id.id in self.brand_id.ids)

    def _get_query(self, allowed_company, store_ids, product_ids):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        attr_value = self.env['res.utility'].get_attribute_code_config()

        sql = f"""
with state_json as (select json_object_agg(xx.value, coalesce(xx.name::json ->> '{user_lang_code}', xx.name::json ->> 'en_US')) as data
                    from ir_model_fields_selection xx
                             join ir_model_fields cc on cc.id = xx.field_id and cc.name = 'state' and cc.model = 'product.defective'),
     attribute_data as (select product_id                         as product_id,
                               json_object_agg(attrs_code, value) as attrs
                        from (select pp.id                                                                                  as product_id,
                                     pa.attrs_code                                                                          as attrs_code,
                                     array_agg(coalesce(pav.name::json ->> '{user_lang_code}', pav.name::json ->> 'en_US')) as value
                              from product_template_attribute_line ptal
                                       left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
                                       left join product_attribute_value_product_template_attribute_line_rel rel
                                                 on rel.product_template_attribute_line_id = ptal.id
                                       left join product_attribute pa on ptal.attribute_id = pa.id
                                       left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
                              where pp.id = any (array{product_ids})
                                and pa.attrs_code notnull
                              group by pp.id, pa.attrs_code) as att
                        group by product_id)
select row_number() over (order by pd.id)                       as stt,
       (select data::json ->> pd.state from state_json)         as trang_thai,
       ''                                                       as so_ct,
       to_char(pd.create_date + interval '{tz_offset} h', 'DD/MM/YYYY')   as ngay_lap_phieu,
       to_char(pd.approval_date + interval '{tz_offset} h', 'DD/MM/YYYY') as ngay_duyet_loi,
       st.code                                                  as ma_cua_hang,
       st.name                                                  as ten_cua_hang,
       pp.barcode                                               as ma_hang,
       coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US') as ten_hang,
       ad.attrs::json -> '{attr_value.get('mau_sac', '')}'      as mau,
       ad.attrs::json -> '{attr_value.get('size', '')}'         as size,
       coalesce(pd.quantity_require, 0)                         as sl_yeu_cau,
       coalesce(pd.quantity_defective_approved, 0)              as sl_duyet,
       coalesce(pd.percent_reduce, 0)                           as phan_tram_gg,
       coalesce(pd.money_reduce, 0)                             as so_tien_giam,
       pd.detail_defective                                      as mo_ta_loi,
       dt.name                                                  as phan_loai_loi,
       rp.name                                                  as nguoi_tao,
       rp2.name                                                 as nguoi_duyet,
       split_part(pc.complete_name, ' / ', 2)                   as nhom_hang,
       split_part(pc.complete_name, ' / ', 3)                   as dong_hang,
       split_part(pc.complete_name, ' / ', 4)                   as ket_cau
from product_defective pd
         left join store st on pd.store_id = st.id
         left join product_product pp on pd.product_id = pp.id
         left join product_template pt on pp.product_tmpl_id = pt.id
         left join product_category pc on pt.categ_id = pc.id
         left join defective_type dt on pd.defective_type_id = dt.id
         join res_users ru on pd.create_uid = ru.id
         join res_partner rp on ru.partner_id = rp.id
         left join res_users ru2 on pd.approval_uid = ru2.id
         left join res_partner rp2 on ru2.partner_id = rp2.id
         left join attribute_data ad on ad.product_id = pd.product_id
where pd.store_id = any(array{store_ids}) 
    and pd.product_id = any(array{product_ids})
    {f'and pd.state = any(array{self.state_ids.mapped("value")})' if self.state_ids else ''}
    {f'and pd.defective_type_id = any(array{self.defective_type_ids.ids})' if self.defective_type_ids else ''}
order by stt
        """
        return sql

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Product = self.env['product.product'].with_context(report_ctx='report.num45,product.product')
        Store = self.env['store'].with_context(report_ctx='report.num45,store')
        product_ids = self.product_ids.ids if self.product_ids else (Product.search([]).ids or [-1])
        store_ids = self.store_ids.ids if self.store_ids else (Store.search([('brand_id', '=', self.brand_id.id)]).ids or [-1])
        query = self._get_query(allowed_company, store_ids, product_ids)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo chi tiết phiếu lỗi')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo chi tiết phiếu lỗi', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 2, f'Thương hiệu: {self.brand_id.name}', formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('trang_thai'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('so_ct'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ngay_lap_phieu'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ngay_duyet_loi'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('ma_cua_hang'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ten_cua_hang'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('ma_hang'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('ten_hang'), formats.get('normal_format'))
            sheet.write(row, 9, ', '.join(value.get('mau') or []), formats.get('normal_format'))
            sheet.write(row, 10, ', '.join(value.get('size') or []), formats.get('normal_format'))
            sheet.write(row, 11, value.get('sl_yeu_cau'), formats.get('int_number_format'))
            sheet.write(row, 12, value.get('sl_duyet'), formats.get('int_number_format'))
            sheet.write(row, 13, (value.get('phan_tram_gg') or 0) / 100, formats.get('percentage_format'))
            sheet.write(row, 14, value.get('so_tien_giam'), formats.get('int_number_format'))
            sheet.write(row, 15, value.get('mo_ta_loi'), formats.get('normal_format'))
            sheet.write(row, 16, value.get('phan_loai_loi'), formats.get('normal_format'))
            sheet.write(row, 17, value.get('nguoi_tao'), formats.get('normal_format'))
            sheet.write(row, 18, value.get('nguoi_duyet'), formats.get('normal_format'))
            sheet.write(row, 19, value.get('nhom_hang'), formats.get('normal_format'))
            sheet.write(row, 20, value.get('dong_hang'), formats.get('normal_format'))
            sheet.write(row, 21, value.get('ket_cau'), formats.get('normal_format'))
            row += 1
