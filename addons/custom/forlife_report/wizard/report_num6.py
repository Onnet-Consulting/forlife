# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval

TITLES = ['STT', 'Nhóm hàng', 'Dòng hàng', 'Mã SP', 'Tên SP', 'Size', 'Màu', 'Giới tính', 'Tổng bán', 'Tổng tồn', 'Nhân viên']
COLUMN_WIDTHS = [10, 20, 20, 15, 30, 20, 20, 20, 20, 20, 20]


class ReportNum6(models.TransientModel):
    _name = 'report.num6'
    _inherit = 'report.base'
    _description = 'Report sale and stock'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    date = fields.Date('Date', required=True)
    start_time = fields.Float('Start time', default=0)
    end_time = fields.Float('End time', default=23 + (59 / 60))
    warehouse_domain = fields.Char('Warehouse', default='[]')

    @api.constrains('start_time', 'end_time')
    def check_times(self):
        for record in self:
            if record.start_time < 0.0 or record.start_time >= record.end_time or record.end_time >= 24.0:
                raise ValidationError(_('Invalid time slot !'))

    def _get_query(self, warehouse_ids, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        attr_value = self.env['res.utility'].get_attribute_code_config()

        start_time = datetime.strptime('{} {:02d}:{:02d}:00'.format(
            self.date, int(self.start_time // 1), int(self.start_time % 1 * 60)), '%Y-%m-%d %H:%S:%M') + relativedelta(hours=-tz_offset)
        end_time = datetime.strptime('{} {:02d}:{:02d}:00'.format(
            self.date, int(self.end_time // 1), int(self.end_time % 1 * 60)), '%Y-%m-%d %H:%S:%M') + relativedelta(hours=-tz_offset)

        where_query = f"""
    sm.company_id = any (array{allowed_company})
    and sm.state = 'done'
    and (src_wh.id = any (array{warehouse_ids}) or des_wh.id = any (array{warehouse_ids}))
    and {format_date_query("sm.date", tz_offset)} <= '{str(self.date)}'
"""
        query = f"""
with stocks as (
    select 
        sm.product_id                                                                            as product_id,
        sum(case when coalesce(src_wh.id, 0) <> 0 then -sm.product_qty else sm.product_qty end)  as qty
    from stock_move sm
        left join stock_location des_lc on sm.location_dest_id = des_lc.id
        left join product_product pp on sm.product_id = pp.id
        left join product_template pt on pp.product_tmpl_id = pt.id
        left join stock_warehouse des_wh on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
        left join stock_location src_lc on sm.location_id = src_lc.id
        left join stock_warehouse src_wh on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
    where {where_query}
    group by sm.product_id
),
sales as (
    select
        pol.product_id  as product_id,
        pol.employee_id as employee_id,
        sum(pol.qty)    as qty
    from pos_order_line pol
        left join pos_order po on pol.order_id = po.id
        left join pos_session ps on ps.id = po.session_id
        left join pos_config pc on ps.config_id = pc.id
        left join store on store.id = pc.store_id
        left join stock_warehouse wh on wh.id = store.warehouse_id and wh.id = any (array{warehouse_ids})
    where po.company_id = any (array{allowed_company})
        and po.state in ('paid', 'done', 'invoiced')
        and po.date_order between '{start_time}'and '{end_time}'
    group by pol.product_id, pol.employee_id
),
products as (
    with temp_tb as (
        select distinct product_id from stocks
        union all
        select distinct product_id from sales
    ) select distinct product_id from temp_tb
),
product_info as (
    select 
        pp.id                                                                   as product_id,
        pp.barcode                                                              as barcode,
        coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US') as product_name,
        split_part(pc.complete_name, ' / ', 2)                          		as product_group,
        split_part(pc.complete_name, ' / ', 3)                          		as product_line
    from product_product pp
        join product_template pt on pp.product_tmpl_id = pt.id
        left join product_category pc on pc.id = pt.categ_id
    where pp.id in (select product_id from products)
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
    where pp.id in (select product_id from products)
    group by pp.id, pa.attrs_code
)
select row_number() over ()                                                       as num,
        pr.product_id                                                             as product_id,
        COALESCE(sa.qty, 0)                                                       as sale_qty,
        COALESCE(sa.employee_id, 0)                                               as employee_id,
        emp.name                                                                  as employee_name,
        COALESCE(st.qty, 0)                                                       as stock_qty,
        pi.barcode                                                                as product_barcode,
        pi.product_name                                                           as product_name,
        pi.product_group                                                          as product_group,
        pi.product_line                                                           as product_line,
        ad_size.value                                                             as product_size,
        ad_color.value                                                            as product_color,
        ad_gender.value                                                           as gender
from products pr
    left join sales sa on sa.product_id = pr.product_id
    left join stocks st on st.product_id = pr.product_id
    left join hr_employee emp on emp.id = sa.employee_id
    left join product_info pi on pi.product_id = pr.product_id
    left join attribute_data ad_size on ad_size.product_id = pr.product_id and ad_size.attrs_code = '{attr_value.get('size', '')}'
    left join attribute_data ad_color on ad_color.product_id = pr.product_id and ad_color.attrs_code = '{attr_value.get('mau_sac', '')}'
    left join attribute_data ad_gender on ad_gender.product_id = pr.product_id and ad_gender.attrs_code = '{attr_value.get('doi_tuong', '')}'
order by num
"""
        return query

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        warehouse_ids = self.env['stock.warehouse'].search(safe_eval(self.warehouse_domain) + [('company_id', 'in', allowed_company), ('brand_id', '=', self.brand_id.id)]).ids or [-1]
        query = self._get_query(warehouse_ids, allowed_company)
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def convert_time(self, value):
        return '{:02d}:{:02d}'.format(int(value), int((value - int(value)) * 60))

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo bán - trưng hàng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo bán - trưng hàng', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Ngày: %s' % self.date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        sheet.write(2, 4, 'Khung giờ từ %s đến %s' % (self.convert_time(self.start_time), self.convert_time(self.end_time)), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, COLUMN_WIDTHS[idx])
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('product_group'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('product_line'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 5, ', '.join(value.get('product_size') or []), formats.get('normal_format'))
            sheet.write(row, 6, ', '.join(value.get('product_color') or []), formats.get('normal_format'))
            sheet.write(row, 7, ', '.join(value.get('gender') or []), formats.get('normal_format'))
            sheet.write(row, 8, value.get('sale_qty'), formats.get('int_number_format'))
            sheet.write(row, 9, value.get('stock_qty'), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('employee_name'), formats.get('normal_format'))
            row += 1
