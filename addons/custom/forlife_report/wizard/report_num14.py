# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Tên chương trình', 'Mã code', 'Số HĐ', 'Số HĐ online', 'Tên KH', 'Mã hàng', 'Tên hàng', 'SL'
]


class ReportNum14(models.TransientModel):
    _name = 'report.num14'
    _inherit = 'report.base'
    _description = 'Search Code Used'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    code = fields.Char(string='Code', required=True)

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
    ppg.name                as program_name,
    pc.name                 as code,
    po.pos_reference        as invoice_num,
    ''                      as invoice_num_online,
    rp.name                 as customer_name,
    pp.default_code         as product_code,
    pol.full_product_name   as product_name,
    pol.qty                 as qty
from promotion_usage_line pul
    join promotion_code pc on pc.id = pul.code_id
    join promotion_program ppg on ppg.id = pul.program_id
    join pos_order_line pol on pol.id = pul.order_line_id
    join pos_order po on po.id = pol.order_id
    join product_product pp on pp.id = pol.product_id
    left join res_partner rp on rp.id = po.partner_id
where po.brand_id = {self.brand_id.id} and pc.name ilike '%{self.code}%'
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
