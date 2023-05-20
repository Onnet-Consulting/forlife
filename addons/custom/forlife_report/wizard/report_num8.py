# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Mã CN', 'Tên CN', 'Mã Voucher', 'Loại Voucher', 'Đối tượng', 'Đầu mã Voucher', 'Bộ phận',
    'Tên chương trình', 'Mục đích sử dụng', 'Hóa đơn sử dụng', 'Ngày sử dụng', 'Giá trị sử dụng'
]


class ReportNum8(models.TransientModel):
    _name = 'report.num8'
    _inherit = 'report.base'
    _description = 'Report voucher detail'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    order_id = fields.Many2one('pos.order', string='Invoice Num')
    voucher = fields.Char(string='Voucher code')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.order_id = False

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        po_conditions = f'and po.id = {self.order_id.id}' if self.order_id else ''
        voucher_conditions = f"and vv.name ilike '%{self.voucher}%'" if self.voucher else ''
        query = f"""
select 
    (select array[coalesce(code, ''), coalesce(name, '')]
     from store where id in (
        select store_id from pos_config where id in (
            select config_id from pos_session where id in (
                select session_id from pos_order where id = po.id 
            )
        )
    ))                                                                      as store_info,
    vv.name 																as voucher_code,
    case when vv.apply_many_times is true then 'Voucher sử dụng nhiều lần'
        else 'Voucher sử dụng 1 lần' end									as voucher_type,
    sv.applicable_object 												 	as object,
    substr(vv.name, 0, 9) 													as voucher_code8,
    hd.name 																as department,
    pv.name 																as program_name,
    ''               														as purpose,
    po.pos_reference 														as order_name,
    to_char(po.date_order + interval '7 hours', 'DD/MM/YYYY')				as date,
    pv_line.price_used														as value
from pos_order po
    join pos_voucher_line pv_line on po.id = pv_line.pos_order_id
    join voucher_voucher vv on vv.id = pv_line.voucher_id
    left join setup_voucher sv on sv.id = vv.purpose_id
    left join program_voucher pv on pv.id = vv.program_voucher_id
    left join hr_department hd on hd.id = vv.derpartment_id
where vv.brand_id = {self.brand_id.id} 
and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
{po_conditions}
{voucher_conditions} 
        """
        return query

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        query = self._get_query()
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values
