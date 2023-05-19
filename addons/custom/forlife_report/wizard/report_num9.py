# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Đầu mã Voucher', 'Bộ phận', 'Loại Voucher', 'Đối tượng', 'Tên chương trình',
    'Mục đích sử dụng', 'SL phát hành', 'Mệnh giá', 'Thành tiền', 'Ngày bắt đầu', 'Ngày kết thúc'
]


class ReportNum9(models.TransientModel):
    _name = 'report.num9'
    _inherit = 'report.base'
    _description = 'Report voucher published'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    voucher = fields.Char(string='Voucher code')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        voucher_conditions = f"and vv.name ilike '%{self.voucher}%'" if self.voucher else ''
        query = f"""
select
    substr(vv.name, 0, 9) 													as voucher_code8,
    hd.name 																as department,
    case when pv.apply_many_times is true then 'Voucher sử dụng nhiều lần'
        else 'Voucher sử dụng 1 lần' end									as voucher_type,
    sv.applicable_object 												 	as object,
    pv.name 																as program_name,
    '' 					                									as purpose,
    0                														as qty_published,
    0                														as value,
    to_char(vv.start_date + interval '7 hours', 'DD/MM/YYYY')				as start_date,
    to_char(vv.end_date + interval '7 hours', 'DD/MM/YYYY')				    as end_date
from program_voucher pv
    join voucher_voucher vv on pv.id = vv.program_voucher_id
    left join setup_voucher sv on sv.id = pv.purpose_id
    left join hr_department hd on hd.id = pv.derpartment_id
where pv.brand_id = {self.brand_id.id}
    and {format_date_query("vv.start_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
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
