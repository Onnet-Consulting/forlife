# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Số PR', 'Ngày PR', 'Số PO', 'Ngày PO', 'NCC', 'Mã hàng', 'Tên hàng', 'SL', 'Đơn giá',
    'CK (%)', 'Thành tiền', 'SL nhập kho', 'SL chưa nhập kho', 'SL lên hóa đơn'
]


class ReportNum13(models.TransientModel):
    _name = 'report.num13'
    _inherit = 'report.base'
    _description = 'Report on the status of PO'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    po_number = fields.Char(string='PO number')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        po_number_list = self.po_number.split(',') if self.po_number else []
        po_number_condition = f"and po.name = any (array{[x.strip('') for x in po_number_list if x]})" if po_number_list else ''
        sql = f"""
select 
    pr.name                                                                 as pr_name,
    to_char(pr.request_date + '{tz_offset} h'::interval, 'DD/MM/YYYY')      as pr_date,
    po.name                                                                 as po_name,
    to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY')        as po_date,
    rp.name                                                                 as suppliers_name,
    pp.barcode                                                              as product_code,
    coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US') as product_name,
    pol.product_qty,
    pol.price_unit,
    pol.discount_percent,
    pol.price_subtotal,
    pol.qty_received,
    pol.product_qty - pol.qty_received                                      as qty_not_received,
    pol.qty_invoiced
from purchase_order_line pol
    join purchase_order po on pol.order_id = po.id
    left join res_partner rp on rp.id = po.partner_id
    left join purchase_request pr on pr.id = po.request_id
    left join product_product pp on pp.id = pol.product_id
    left join product_template pt on pt.id = pp.product_tmpl_id
where {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'
    and pol.company_id = {self.company_id.id}
    {po_number_condition}
order by po.date_order desc 
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
