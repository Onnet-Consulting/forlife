# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Mã cửa hàng', 'Tên cửa hàng', 'Tổng điểm tích', 'Tổng điểm tiêu',
    'Tổng điểm trả', 'Tổng điểm hoàn', 'Tổng điểm tích bù', 'Tổng điểm đã reset'
]


class ReportNum24(models.TransientModel):
    _name = 'report.num24'
    _inherit = 'report.base'
    _description = 'Point customer report'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_id = fields.Many2one('store', string='Store')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_id = False

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        stores = self.store_id.ids or self.env['store'].search([('brand_id', '=', self.brand_id.id)]).ids or [-1]
        brand = {
            'FMT': 'format',
            'TKL': 'forlife',
        }
        query = f"""
with datas as (select pc.store_id                                                                                  as store_id,
                      sum(case when php.point_order_type = 'new' then php.points_fl_order else 0 end)              as tich,
                      sum(php.points_used)                                                                         as tieu,
                      sum(case when php.point_order_type = 'back_order' then php.points_back else 0 end)           as tra,
                      sum(case when php.point_order_type = 'back_order' then php.points_fl_order else 0 end)       as hoan,
                      sum(case when php.point_order_type = 'point compensate' then php.points_fl_order else 0 end) as bu,
                      sum(case when php.point_order_type = 'reset_order' then php.points_store else 0 end)         as reset
               from partner_history_point php
                        join pos_order po on php.pos_order_id = po.id
                        join pos_session ps on po.session_id = ps.id
                        join pos_config pc on ps.config_id = pc.id
               where {format_date_query("php.create_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
                   and php.store = '{brand.get(self.brand_id.code) or ''}'
                   and pc.store_id = any(array{stores})
               group by pc.store_id)
select row_number() over () as stt,
       store.code           as ma_cua_hang,
       store.name           as ten_cua_hang,
       datas.tich           as tich,
       datas.tieu           as tieu,
       datas.tra            as tra,
       datas.hoan           as hoan,
       datas.bu             as bu,
       datas.reset          as reset
from datas
         join store on store.id = datas.store_id
order by stt
"""
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tích - tiêu điểm theo cửa hàng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo tích - tiêu điểm theo cửa hàng', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ma_cua_hang'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ten_cua_hang'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('tich'), formats.get('int_number_format'))
            sheet.write(row, 4, value.get('tieu'), formats.get('int_number_format'))
            sheet.write(row, 5, value.get('tra'), formats.get('int_number_format'))
            sheet.write(row, 6, value.get('hoan'), formats.get('int_number_format'))
            sheet.write(row, 7, value.get('bu'), formats.get('int_number_format'))
            sheet.write(row, 8, value.get('reset'), formats.get('int_number_format'))
            row += 1
