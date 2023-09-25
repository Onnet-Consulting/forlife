# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.tools import float_round

TITLES = [
    'STT', 'Mã lệnh sản xuất', 'Kho/xưởng', 'Mã vật tư', 'Tên vật tư', 'Đơn vị tính vật tư', 'Số lượng sản xuất theo kế hoạch ',
    'Số lượng sản xuất nhập kho thực tế', 'Số lượng vât tư  tiêu hao theo nhập kho thực tế', 'Số lượng vật tư kho cấp', 'Chênh lệch'
]


class ReportNum41(models.TransientModel):
    _name = 'report.num41'
    _inherit = 'report.base'
    _description = 'Báo cáo quyết toán lệnh sản xuất'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    leader_id = fields.Many2one('hr.employee', string='Quản lý đơn hàng')
    machining_id = fields.Many2one('res.partner', string='Đơn vị gia công')
    production_ids = fields.Many2many('forlife.production', 'report_num41_production_rel', string='Lệnh sản xuất')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('leader_id', 'machining_id')
    def onchange_leader_machining(self):
        self.production_ids = self.production_ids.filtered(lambda f: f.leader_id.id == self.leader_id.id and f.machining_id.id == self.machining_id.id)

    def _get_query(self, production_ids):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset

        query_final = f"""
with forlife_production_x as (select id
                              from forlife_production
                               where {format_date_query("created_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
                                and id = any(array{production_ids})),
     wh_data as (select json_object_agg(production_id, warehouse) as value
                 from (select row_number() over (PARTITION BY foior.production_id) as stt,
                              foior.production_id                                  as production_id,
                              concat('[', wh.code, ']', wh.name)                   as warehouse
                       from forlife_other_in_out_request foior
                                join stock_location sl on foior.location_id = sl.id and sl.code in ('N0101', 'N0103')
                                join stock_location sl2 on foior.location_material_id = sl2.id
                                join stock_warehouse wh on sl2.warehouse_id = wh.id
                       where foior.production_id in (select id from forlife_production_x)
                         and foior.status = 'done') as xx
                 where stt = 1),
     sl_chi_tiet as (select fp.id,
                            fpm.product_id,
                            fpfp.produce_qty,
                            fpfp.stock_qty,
                            fpm.rated_level * fpm.conversion_coefficient * (1 + fpm.loss / 100) * fpfp.stock_qty as tieu_hao
                     from forlife_production fp
                              join forlife_production_finished_product fpfp on fp.id = fpfp.forlife_production_id
                              join forlife_production_material fpm on fpfp.id = fpm.forlife_production_id
                     where fp.id in (select id from forlife_production_x)),
     x_sl_sx_ke_hoach as (select json_object_agg(concat(id, '-', product_id), value) as data
                          from (select id,
                                       product_id,
                                       sum(produce_qty) as value
                                from sl_chi_tiet
                                group by id, product_id) as xx),
     x_sl_nk_thuc_te as (select json_object_agg(concat(id, '-', product_id), value) as data
                         from (select id,
                                      product_id,
                                      sum(stock_qty) as value
                               from sl_chi_tiet
                               group by id, product_id) as xx),
     x_sl_vt_tieu_hao as (select json_object_agg(concat(id, '-', product_id), value) as data
                          from (select id,
                                       product_id,
                                       sum(tieu_hao) as value
                                from sl_chi_tiet
                                group by id, product_id) as xx1),
     sl_vt_dieu_chuyen as (select json_object_agg(concat(fp_id, '-', product_id), qty_in) as data
                           from (select stl.work_to                  as fp_id,
                                        stl.product_id,
                                        sum(coalesce(stl.qty_in, 0)) as qty_in
                                 from stock_transfer st
                                          join stock_transfer_line stl on st.id = stl.stock_transfer_id
                                 where stl.work_to in (select id from forlife_production_x)
                                   and st.state = 'done'
                                 group by stl.work_to, stl.product_id) as xx2)
select row_number() over (order by fp.code, fp.id)                                                     as stt,
       fp.code                                                                                         as ma_lenh_sx,
       (select value::json ->> fp.id::text from wh_data)                                               as kho_xuong,
       pp.barcode                                                                                      as ma_vat_tu,
       coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US')                       as ten_vat_tu,
       coalesce(uom.name::json ->> '{user_lang_code}', uom.name::json ->> 'en_US')                     as dvt,
       coalesce((select data::json ->> concat(fp.id, '-', pp.id) from x_sl_sx_ke_hoach)::float, 0)     as sl_sx_ke_hoach,
       coalesce((select data::json ->> concat(fp.id, '-', pp.id) from x_sl_nk_thuc_te)::float, 0)      as sl_nk_thuc_te,
       coalesce((select data::json ->> concat(fp.id, '-', pp.id) from x_sl_vt_tieu_hao)::float4, 0)    as sl_vt_tieu_hao_tt,
       coalesce((select data::json ->> concat(fp.id, '-', pp.id) from sl_vt_dieu_chuyen)::float4, 0)   as sl_vt_dieu_chuyen,
       uom.rounding,
       case when uom.rounding >= 1 then 0 else LENGTH(SUBSTRING(uom.rounding::text FROM '\.(.*)')) end as precision_rounding
from forlife_production fp
         join production_material_import pmi on fp.id = pmi.production_id
         join product_product pp on pmi.product_id = pp.id
         join product_template pt on pp.product_tmpl_id = pt.id
         join uom_uom uom on pt.uom_id = uom.id
where fp.id in (select id from forlife_production_x)
order by stt
"""
        return query_final

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Utility = self.env['res.utility']
        ForLifeProduction = self.env['forlife.production'].with_context(order_manager=self.leader_id.id, machining=self.machining_id.id, received=1)
        production_ids = self.production_ids.ids if self.production_ids else (
                ForLifeProduction.search([('create_date', '>=', self.from_date), ('create_date', '<=', self.to_date)]).ids or [-1])
        query = self._get_query(production_ids)
        data = Utility.execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo quyết toán lệnh sản xuất')
        sheet.set_row(0, 30)
        sheet.set_row(4, 30)
        sheet.write(0, 0, 'Báo cáo quyết toán lệnh sản xuất', formats.get('header_format'))
        sheet.write(2, 0, f"Từ ngày: {self.from_date.strftime('%d/%m/%Y')} đến ngày {self.to_date.strftime('%d/%m/%Y')}", formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(TITLES) - 1, 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ma_lenh_sx'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('kho_xuong'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ma_vat_tu'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ten_vat_tu'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('dvt'), formats.get('normal_format'))
            sheet.write(row, 6, float_round(value=value.get('sl_sx_ke_hoach') or 0, precision_rounding=value.get('rounding') or 0), formats.get('right_format'))
            sheet.write(row, 7, float_round(value=value.get('sl_nk_thuc_te') or 0, precision_rounding=value.get('rounding') or 0), formats.get('right_format'))
            sheet.write(row, 8, float_round(value=value.get('sl_vt_tieu_hao_tt') or 0, precision_rounding=value.get('rounding') or 0), formats.get('right_format'))
            sheet.write(row, 9, float_round(value=value.get('sl_vt_dieu_chuyen') or 0, precision_rounding=value.get('rounding') or 0), formats.get('right_format'))
            sheet.write(row, 10, float_round(value=(value.get('sl_vt_dieu_chuyen') or 0) - (value.get('sl_vt_tieu_hao_tt') or 0), precision_rounding=value.get('rounding') or 0), formats.get('right_format'))
            row += 1
