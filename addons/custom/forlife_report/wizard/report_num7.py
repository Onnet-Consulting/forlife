# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = ['STT', 'Dòng hàng', 'Số lượng', 'Doanh thu', '% danh thu']


class ReportNum7(models.TransientModel):
    _name = 'report.num7'
    _inherit = 'report.base'
    _description = 'Report in-store revenue by product line'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    employee_ids = fields.Many2many('hr.employee', string='Employee KD')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.warehouse_ids = False
        self.employee_ids = False

    @api.onchange('all_warehouses', 'warehouse_ids')
    def onchange_warehouse(self):
        self.employee_ids = False
        return {'domain': {'employee_ids': [('id', 'in', self.get_employees())]}}

    def get_employees(self):
        wh = self.env['stock.warehouse'].search([]) if self.all_warehouses else self.warehouse_ids
        if not self.brand_id or not wh:
            return []
        query = f"""
select array_agg(emp_id) as ids from (
    select DISTINCT hr_employee_id as emp_id from hr_employee_store_rel where store_id in (
        select id from store where brand_id = {self.brand_id.id} and warehouse_id = any (array{wh.ids}))) as data
"""
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        return data[0].get('ids', [])

    def _get_query(self, store_ids):
        self.ensure_one()
        tz_offset = self.tz_offset
        employee_conditions = f'and pol.employee_id = any (array{self.employee_ids.ids})' if self.employee_ids else ''

        query = f"""
with product_line_data as (
    select 
        pp.id 								 	              as product_id,
        coalesce(split_part(pc.complete_name, ' / ', 3), '')  as product_line
    from  product_product pp
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join product_category pc on pc.id = pt.categ_id
),
po_line as (
    select 
        pld.product_line                                                                      as product_line,
        pol.qty                                                                               as qty,
        case when pol.qty > 0 then pol.price_subtotal_incl else -pol.price_subtotal_incl end  as revenue
    from pos_order_line pol
        join pos_order po on po.id = pol.order_id and po.state in ('paid', 'done', 'invoiced')
        join product_product pp on pp.id = pol.product_id
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join product_line_data pld on pld.product_id = pol.product_id
    where po.session_id in (select id from pos_session where config_id in (select id from pos_config where store_id = any (array{store_ids})))
        and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
        {employee_conditions}
)
select product_line                                             as product_line,
        sum(qty)                                                as qty,
        sum(revenue)                                            as revenue,
        sum(revenue) / (select sum(revenue) from po_line) * 100 as percent_revenue
from po_line
group by product_line
"""
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        warehouse_ids = self.env['stock.warehouse'].search([('brand_id', '=', self.brand_id.id), ('company_id', 'in', allowed_company)]).ids if self.all_warehouses else self.warehouse_ids.ids
        store_ids = self.env['store'].search([('warehouse_id', 'in', warehouse_ids)]).ids or [-1]
        query = self._get_query(store_ids)
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values
