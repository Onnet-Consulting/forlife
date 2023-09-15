# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Ngày', 'Mã cửa hàng', 'Tên cửa hàng',
    'Phiên bán hàng', 'Số đơn hàng', 'Khách hàng',
    'Diễn giải', 'Số tiền', 'Hình thức thanh toán',
    'Trạng thái phiên'
]


class ReportNum43(models.TransientModel):
    _name = 'report.num43'
    _inherit = 'report.base'
    _description = 'Báo cáo hình thức thanh toán trên POS'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    brand_id = fields.Many2one('res.brand', string='Thương hiệu', required=True)
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    pos_order = fields.Char(string='Số đơn hàng')
    pos_reference = fields.Char(string='Diễn giải')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def _get_query(self, allowed_company):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        sql = f"""
            select 
                row_number() over (order by pp.payment_date) as num,
                to_char(pp.payment_date + '{tz_offset} h'::interval, 'DD/MM/YYYY') as ngay_tt,
                st.code as ma_ch,
                st.name as ten_ch,
                ps.name as phien_bh,
                po.name as so_dh,
                rp.name as ten_kh,
                po.pos_reference as dien_giai,
                pp.amount as so_tien,
                coalesce (ppm.name->> 'vi_VN', ppm.name->> 'en_US') as hinhthuc_tt,
                ps.state as tt_phien
            from pos_order po
            left join res_partner rp on po.partner_id = rp.id
            left join pos_session ps on po.session_id = ps.id
            left join pos_config pc on ps.config_id = pc.id
            left join store st on pc.store_id = st.id
            left join pos_payment pp on po.id = pp.pos_order_id 
            left join pos_payment_method ppm on pp.payment_method_id = ppm.id
            where {format_date_query("po.date_order", tz_offset)} between '{self.from_date}' and '{self.to_date}'        
        """

        if self.brand_id:
            sql += f" and st.brand_id = {self.brand_id.id}"
        if self.partner_id:
            sql += f" and rp.id = {self.partner_id.id}"
        if self.pos_order:
            sql += f" and po.name like '%{self.pos_order}%'"
        if self.pos_reference:
            sql += f" and po.name like '%{self.pos_reference}%'"

        sql += ' order by st.brand_id, pp.payment_date, st.id, ppm.id, ps.id'
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
        sheet = workbook.add_worksheet('Báo cáo hình thức thanh toán trên POS')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo hình thức thanh toán trên POS', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 2, 'Thương hiệu: %s' % (self.brand_id.name or ''), formats.get('italic_format'))
        sheet.write(2, 4, 'Khách hàng: %s' % (self.partner_id.name or ''), formats.get('italic_format'))
        sheet.write(2, 6, 'Đơn hàng: %s' % (self.pos_order or ''), formats.get('italic_format'))
        sheet.write(2, 8, 'Diễn giải: %s' % (self.pos_reference or ''), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ngay_tt'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ma_ch'), formats.get('center_format'))
            sheet.write(row, 3, value.get('ten_ch'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('phien_bh'), formats.get('center_format'))
            sheet.write(row, 5, value.get('so_dh'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('ten_kh'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('dien_giai'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('so_tien'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('hinhthuc_tt'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('tt_phien'), formats.get('normal_format'))
            row += 1
