# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

TITLES = [
    'STT', 'KHU VỰC', 'MÃ CỬA HÀNG', 'TÊN CỬA HÀNG', 'MÃ NHÂN VIÊN', 'TÊN NHÂN VIÊN', 'VỊ TRÍ', 'VỊ TRÍ KIÊM NHIỆM',
    'SỐ BILL', 'TB BILL', 'TỔNG CỘNG', 'MỤC TIÊU CÁ NHÂN', 'MỤC TIÊU CỬA HÀNG', 'THU NHẬP DỰ TÍNH'
]


class ReportNum25(models.TransientModel):
    _name = 'report.num25'
    _inherit = 'report.base'
    _description = 'Estimated income by revenue report'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    bo_plan_id = fields.Many2one('business.objective.plan', string='BO Plan', required=True)
    store_id = fields.Many2one('store', string='Store')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    sale_province_id = fields.Many2one('res.sale.province', 'Sale Province')
    view_type = fields.Selection([('by_day', 'By day'), ('by_month', 'By month')], string='View type', required=True, default='by_day')

    @api.constrains('from_date', 'to_date', 'bo_plan_id')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))
            bo_plan_id = record.bo_plan_id
            if record.from_date and record.to_date and bo_plan_id and (record.from_date < bo_plan_id.from_date or record.to_date > bo_plan_id.to_date):
                raise ValidationError(_("Date must be between '%s' and '%s'") % (bo_plan_id.from_date.strftime('%d/%m/%Y'), bo_plan_id.to_date.strftime('%d/%m/%Y')))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_id = False
        self.bo_plan_id = False

    @api.onchange('bo_plan_id')
    def onchange_bo_plan(self):
        self.from_date = self.bo_plan_id.from_date
        self.to_date = self.bo_plan_id.to_date

    @api.onchange('store_id')
    def onchange_store(self):
        self.employee_id = False
        return {'domain': {'employee_id': [('id', 'in', self.store_id.employee_ids.ids)]}}

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        employee_conditions = 'pol.employee_id notnull' if not self.employee_id else f'pol.employee_id = {str(self.employee_id.id)}'

        sql = f"""
with uom_name_by_id as (
    select
        id,
        coalesce(name::json ->> '{user_lang_code}', name::json ->> 'en_US') as name
    from uom_uom
),
order_line_data as (
    select 
        concat(pol.employee_id || '-' || po.id) 												    as key_invoice,
        pol.employee_id																			    as employee_id,
        emp.name 																				    as employee_name,
        emp.code  																		 		    as employee_code,
        po.pos_reference  																		    as pos_reference,
        rp.name  																				    as customer_name,
        rp.ref  																				    as customer_code,
        rp.phone  																				    as customer_phone,
        pol.product_id  																		    as product_id,
        pp.default_code 																		    as product_code,
        pol.full_product_name 																 	    as product_name,
        uom.name                                                								    as uom_name,
        to_char(po.date_order + interval '{tz_offset} hours', 'DD/MM/YYYY')                         as by_day,
        to_char(po.date_order + interval '{tz_offset} hours', 'MM/YYYY')		                    as by_month,
        greatest(pol.qty, 0)                                                                        as sale_qty,
        - least(pol.qty, 0)                                                                         as refund_qty,
        coalesce(pol.original_price, 0)    												 		    as lst_price,
        coalesce((select sum(
            case when type = 'point' then recipe * 1000
                when type = 'card' then recipe
                when type = 'ctkm' then discounted_amount
                else 0
            end
        ) from pos_order_line_discount_details where pos_order_line_id = pol.id), 0)		        as money_reduced,
        po.note 																 		 		    as note
    from pos_order_line pol
        join pos_order po on po.id = pol.order_id and po.state in ('paid', 'done', 'invoiced')
        join product_product pp on pp.id = pol.product_id
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join hr_employee emp on emp.id = pol.employee_id
        left join res_partner rp on rp.id = po.partner_id
        left join uom_name_by_id uom on uom.id = pt.uom_id
    where {employee_conditions} and pol.qty <> 0 and pt.detailed_type <> 'service' and (pt.voucher = false or pt.voucher is null)
        and po.session_id in (select id from pos_session where config_id in (select id from pos_config where store_id = {str(self.store_id.id)}))
        and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
    order by employee_id
),
data_group as (
    select key_invoice,
        employee_id,
        product_id,
        product_code,
        product_name,
        by_day as date,
        sum(sale_qty) as sale_qty,
        sum(refund_qty) as refund_qty,
        uom_name,
        lst_price,
        coalesce(sum(money_reduced), 0) as money_reduced,
        sum(abs((sale_qty * lst_price) - (refund_qty * lst_price) - money_reduced)) as price_subtotal
    from order_line_data
    group by key_invoice,
        employee_id,
        product_id,
        product_code,
        product_name,
        by_day,
        uom_name,
        lst_price
),
detail_data_invoice_list as (
    select employee_id, json_object_agg(key_invoice, order_detail) as detail_invoice from (
        select employee_id, key_invoice , array_agg(to_json(dg.*)) as order_detail
        from data_group as dg group by employee_id, key_invoice
    ) as order_detail_data_by_employee group by employee_id
),
prepare_value_data_invoice_list as (
    select employee_id,
        key_invoice,
        by_day as date,
        pos_reference,
        employee_name,		
        customer_name,
        customer_code,
        customer_phone,
        sum(sale_qty) as sale_qty,
        sum(refund_qty) as refund_qty,
        sum(sale_qty * lst_price) as tt,
        sum(money_reduced) as money_reduced,
        sum(0) as gg_bill,
        sum(refund_qty * lst_price) as refund,
        note
    from order_line_data
    group by employee_id,
        key_invoice,
        by_day,
        pos_reference,
        employee_name,		
        customer_name,
        customer_code,
        customer_phone,
        note
    order by employee_id
),
value_data_invoice_list as (
    select employee_id, array_agg(to_json(inv_info.*)) as value_invoice
    from prepare_value_data_invoice_list as inv_info group by employee_id
),
total_by_time as (
    select employee_id, json_object_agg({self.view_type}, total) as qty_by_time from (
        select employee_id,
            {self.view_type},
            sum((sale_qty * lst_price) - (refund_qty * lst_price) - money_reduced) as total
        from order_line_data group by employee_id, {self.view_type}
    ) as tb_by_time group by employee_id
),
employee_list as (
    select DISTINCT employee_id, employee_name, employee_code from order_line_data
)
select employee.employee_id,
    employee.employee_name,
    employee.employee_code,
    tbt.qty_by_time,
    vdil.value_invoice,
    ddil.detail_invoice
from employee_list employee 
    left join total_by_time tbt on employee.employee_id = tbt.employee_id
    left join detail_data_invoice_list ddil on employee.employee_id = ddil.employee_id
    left join value_data_invoice_list vdil on employee.employee_id = vdil.employee_id        
"""
        return sql

    def get_title_with_view_type(self, from_date, to_date, view_type):
        format_date, day, month = ('%d/%m/%Y', 1, 0) if view_type == 'by_day' else ('%m/%Y', 0, 1)
        title = []
        while from_date <= to_date:
            title.append(from_date.strftime(format_date))
            from_date = from_date + relativedelta(months=month, days=day)
        if to_date.strftime(format_date) not in title:
            title.append(to_date.strftime(format_date))
        return title

    def format_data(self, data):
        res = []
        column_add = self.get_title_with_view_type(self.from_date, self.to_date, self.view_type)
        TITLES.extend(column_add)
        value_invoice_by_employee_id = {}
        detail_invoice_by_order_key = {}
        for value in data:
            qty_by_time = value.pop('qty_by_time')
            value_invoice_by_employee_id.update({value['employee_id']: value.pop('value_invoice')})
            detail_invoice_by_order_key.update(value.pop('detail_invoice'))
            total_amount = 0
            for c in column_add:
                amount = qty_by_time.get(c, 0) or 0
                value[c] = amount
                total_amount += amount
            value['total_amount'] = total_amount
            res.append(value)
        return {
            'titles': TITLES,
            'data': res,
            'column_add': column_add,
        }

    def get_data(self, allowed_company):
        self.ensure_one()
        values = super().get_data(allowed_company)
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update(self.format_data(data))
        return values