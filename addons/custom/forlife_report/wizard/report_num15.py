# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Chi nhánh', 'Bộ phận', 'Ngày', 'Số HĐ', 'Tên KH', 'Voucher', 'Tên chương trình', 'Bắt đầu', 'Kết thúc'
]


class ReportNum15(models.TransientModel):
    _name = 'report.num15'
    _inherit = 'report.base'
    _description = 'Search Voucher Used'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    voucher = fields.Char(string='Voucher', required=True)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        sql = f"""
select
    (select name from store where id in (
        select store_id from pos_config where id in (
            select config_id from pos_session where id = po.session_id
            ) 
        ) limit 1
    )                                                                   as store_name,
    hd.name                                                             as department,
    to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY')    as date,
    po.pos_reference                                                    as invoice_num,
    rp.name                                                             as customer_name,
    vv.name                                                             as voucher,
    pv.name                                                             as program_name,
    to_char(vv.start_date + '{tz_offset} h'::interval, 'DD/MM/YYYY')    as start_date,
    to_char(vv.end_date + '{tz_offset} h'::interval, 'DD/MM/YYYY')      as end_date
from pos_voucher_line pvl
    join voucher_voucher vv on vv.id = pvl.voucher_id
    join program_voucher pv on pv.id = vv.program_voucher_id
    join hr_department hd on hd.id = pv.derpartment_id
    join pos_order po on po.id = pvl.pos_order_id
    left join res_partner rp on rp.id = po.partner_id
where po.brand_id = {self.brand_id.id} and vv.name ilike '%{self.voucher}%'
  and {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
"""
        return sql

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
