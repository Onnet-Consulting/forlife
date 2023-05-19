# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval

TITLES = ['STT', 'Nhóm hàng', 'Dòng hàng', 'Mã SP', 'Tên SP', 'Size', 'Màu', 'Giới tính', 'Tổng bán', 'Tổng tồn', 'Nhân viên']


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
)
select pr.product_id                                                              as product_id,
        COALESCE(sa.qty, 0)                                                       as sale_qty,
        COALESCE(sa.employee_id, 0)                                               as employee_id,
        emp.name                                                                  as employee_name,
        COALESCE(st.qty, 0)                                                       as stock_qty,
        (select barcode from product_info where product_id = pr.product_id)       as product_barcode,
        (select product_name from product_info where product_id = pr.product_id)  as product_name,
        (select product_group from product_info where product_id = pr.product_id) as product_group,
        (select product_line from product_info where product_id = pr.product_id)  as product_line,
        ''                                                                        as product_size,
        ''                                                                        as product_color,
        ''                                                                        as gender
from products pr
    left join sales sa on sa.product_id = pr.product_id
    left join stocks st on st.product_id = pr.product_id
    left join hr_employee emp on emp.id = sa.employee_id
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
