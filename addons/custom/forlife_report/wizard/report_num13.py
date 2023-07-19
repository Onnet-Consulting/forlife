# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Số PR', 'Ngày PR', 'Số PO', 'Ngày PO', 'NCC', 'Mã SKU', 'Barcode', 'Tên hàng', 'SL',
    'Đơn giá', 'CK (%)', 'Thành tiền', 'SL nhập kho', 'SL chưa nhập kho', 'SL lên hóa đơn'
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

    def _get_query(self, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        po_number_list = self.po_number.split(',') if self.po_number else []
        po_number_condition = f"and po.name = any (array{[x.strip('') for x in po_number_list if x]})" if po_number_list else ''
        sql = f"""
select row_number() over (order by po.date_order desc)                      as num,
    pr.name                                                                 as pr_name,
    to_char(pr.request_date + '{tz_offset} h'::interval, 'DD/MM/YYYY')      as pr_date,
    po.name                                                                 as po_name,
    to_char(po.date_order + '{tz_offset} h'::interval, 'DD/MM/YYYY')        as po_date,
    rp.name                                                                 as suppliers_name,
    pt.sku_code                                                             as sku_code,
    pp.barcode                                                              as barcode,
    coalesce(pt.name::json ->> '{user_lang_code}', pt.name::json ->> 'en_US') as product_name,
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
    and pol.company_id = any(array{allowed_company})
    {po_number_condition}
order by num
"""
        return sql

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query(allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tình hình thực hiện đơn hàng mua')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo tình hình thực hiện đơn hàng mua', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 2, 'Số YC: %s' % (self.po_number or ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('pr_name'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('pr_date'), formats.get('center_format'))
            sheet.write(row, 3, value.get('po_name'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('po_date'), formats.get('center_format'))
            sheet.write(row, 5, value.get('suppliers_name'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('sku_code'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('barcode'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('product_qty', 0), formats.get('float_number_format'))
            sheet.write(row, 10, value.get('price_unit', 0), formats.get('int_number_format'))
            sheet.write(row, 11, value.get('discount_percent', 0), formats.get('float_number_format'))
            sheet.write(row, 12, value.get('price_subtotal', 0), formats.get('int_number_format'))
            sheet.write(row, 13, value.get('qty_received', 0), formats.get('float_number_format'))
            sheet.write(row, 14, value.get('qty_not_received', 0), formats.get('float_number_format'))
            sheet.write(row, 15, value.get('qty_invoiced', 0), formats.get('float_number_format'))
            row += 1
