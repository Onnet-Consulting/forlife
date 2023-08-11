# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = ['STT', 'Cửa hàng', 'Hạng thẻ', 'Thuế suất', 'Giá trị trước thuế', 'Thuế GTGT', 'Tổng giá trị ưu đãi']


class ReportNum23(models.TransientModel):
    _name = 'report.num23'
    _inherit = 'report.base'
    _description = 'Card rank discount report'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_ids = fields.Many2many('store', string='Store')
    type = fields.Selection([('time', _('Time')), ('store', _('Store'))], 'Group by', default='store', required=True)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_ids = self.store_ids.filtered(lambda f: f.brand_id == self.brand_id)

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset

        _type = {
            'time': '''
select 0                           as stt,
       ngay                        as ngay,
       to_char(ngay, 'DD/MM/YYYY') as cua_hang,
       null                        as hang,
       null                        as thue_suat,
       gia_tri_truoc_thue::float4  as gia_tri_truoc_thue,
       thue_gtgt::float4           as thue_gtgt,
       tong_tien::float4           as tong_tien
from data_by_day
union all
select row_number() over (PARTITION BY ngay order by thue_suat) as stt,
       ngay                                             as ngay,
       cua_hang                                         as cua_hang,
       hang                                             as hang,
       thue_suat                                        as thue_suat,
       gia_tri_truoc_thue::float4                       as gia_tri_truoc_thue,
       thue_gtgt::float4                                as thue_gtgt,
       tong_tien::float4                                as tong_tien
from datas
order by ngay desc, stt''',
            'store': '''
select 0                                            as stt,
       null                                         as cua_hang,
       null                                         as hang,
       null                                         as thue_suat,
       coalesce(sum(gia_tri_truoc_thue)::float4, 0) as gia_tri_truoc_thue,
       coalesce(sum(thue_gtgt)::float4, 0)          as thue_gtgt,
       coalesce(sum(tong_tien)::float4, 0)          as tong_tien
from datas
union all
select row_number() over (order by cua_hang, hang, thue_suat) as stt,
       cua_hang                                               as cua_hang,
       hang                                                   as hang,
       thue_suat                                              as thue_suat,
       sum(gia_tri_truoc_thue)::float4                        as gia_tri_truoc_thue,
       sum(thue_gtgt)::float4                                 as thue_gtgt,
       sum(tong_tien)::float4                                 as tong_tien
from datas
group by cua_hang, hang, thue_suat
order by stt''',
        }

        query = f"""
with datas as (select (po.date_order + interval '{tz_offset} hours')::date                    as ngay,
                      store.name                                                              as cua_hang,
                      cr.name                                                                 as hang,
                      coalesce(at.amount, 0)                                                  as thue_suat,
                      sum(poldd.recipe / (1 + coalesce(at.amount, 0) / 100))                  as gia_tri_truoc_thue,
                      sum(poldd.recipe - (poldd.recipe / (1 + coalesce(at.amount, 0) / 100))) as thue_gtgt,
                      sum(poldd.recipe)                                                       as tong_tien
               from pos_order_line_discount_details as poldd
                        join pos_order_line pol on poldd.pos_order_line_id = pol.id
                        join pos_order po on pol.order_id = po.id
                        join pos_session ps on po.session_id = ps.id
                        join pos_config pc on ps.config_id = pc.id
                        join store on pc.store_id = store.id
                        join member_card mc on po.card_rank_program_id = mc.id
                        join card_rank cr on mc.card_rank_id = cr.id
                        left join account_tax_pos_order_line_rel tax_rel on tax_rel.pos_order_line_id = pol.id
                        left join account_tax at on at.id = tax_rel.account_tax_id
               where type = 'card'
                and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}' 
                and {f'store.id = any(array{self.store_ids.ids})' if self.store_ids else f'store.brand_id = {self.brand_id.id}'}
               group by ngay, cua_hang, hang, thue_suat
               order by ngay),
     data_by_day as (select ngay                    as ngay,
                            sum(gia_tri_truoc_thue) as gia_tri_truoc_thue,
                            sum(thue_gtgt)          as thue_gtgt,
                            sum(tong_tien)          as tong_tien
                     from datas
                     group by ngay)
{_type.get(self.type)}
"""
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data if len(data) > 1 else [],
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo giá trị chiết khấu hạng thẻ')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo giá trị chiết khấu hạng thẻ', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            if value.get('stt') == 0:
                sheet.write(row, 0, '', formats.get('subtotal_format'))
                sheet.write(row, 1, value.get('cua_hang'), formats.get('subtotal_format'))
                sheet.write(row, 2, value.get('hang'), formats.get('subtotal_format'))
                sheet.write(row, 2, value.get('hang'), formats.get('subtotal_format'))
                sheet.write(row, 3, '', formats.get('subtotal_format'))
                sheet.write(row, 4, value.get('gia_tri_truoc_thue'), formats.get('int_subtotal_format'))
                sheet.write(row, 5, value.get('thue_gtgt'), formats.get('int_subtotal_format'))
                sheet.write(row, 6, value.get('tong_tien'), formats.get('int_subtotal_format'))
            else:
                sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
                sheet.write(row, 1, value.get('cua_hang'), formats.get('normal_format'))
                sheet.write(row, 2, value.get('hang'), formats.get('normal_format'))
                sheet.write(row, 3, f"{value.get('thue_suat') or 0}", formats.get('percentage_format'))
                sheet.write(row, 4, value.get('gia_tri_truoc_thue'), formats.get('int_number_format'))
                sheet.write(row, 5, value.get('thue_gtgt'), formats.get('int_number_format'))
                sheet.write(row, 6, value.get('tong_tien'), formats.get('int_number_format'))
            row += 1
