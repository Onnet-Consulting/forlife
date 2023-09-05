# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

TITLES = [
    'STT', 'Mã lệnh sản xuất', 'Kho/xưởng', 'Mã vật tư', 'Số lượng sản xuất kế hoạch', 'Số lượng nhập kho thực tế',
    'Số lượng tiêu hao thực tế', 'Số lượng vật tư kho cấp', 'Chênh lệch quyết toán'
]


class ReportNum41(models.TransientModel):
    _name = 'report.num41'
    _inherit = 'report.base'
    _description = 'Báo cáo quyết toán lệnh sản xuất'

    date = fields.Date(string='Date', required=True)
    employee_id = fields.Many2one('hr.employee', string='Quản lý đơn hàng')
    partner_id = fields.Many2one('res.partner', string='Đơn vị gia công')
    production_ids = fields.Many2many('forlife.production', 'report_num41_production_rel', string='Lệnh sản xuất')

    def _get_query(self):
        self.ensure_one()

        query_final = f"""
            select row_number() over (order by fp.id) as stt,
                   fp.code                            as ma_lenh_sx,
                   ''                                 as kho_xuong,
                   pp.barcode                         as ma_vat_tu,
                   coalesce(fpfp.produce_qty, 0)      as sl_sx_ke_hoach,
                   coalesce(fpfp.stock_qty, 0)        as sl_nk_thuc_te,
                   0 as sl_th_thuc_te,
                   0 as sl_vt_kho_cap,
                   0 as chenh_lech_qt
            from forlife_production fp
                     join forlife_production_finished_product fpfp on fp.id = fpfp.forlife_production_id
                     join product_product pp on fpfp.product_id = pp.id
            where fp.created_date = '{self.date}'
                {f'and fp.leader_id = {self.employee_id.id}' if self.employee_id else ''}
                {f'and fp.machining_id = {self.partner_id.id}' if self.partner_id else ''}
                {f'and fp.id = any(array{self.production_ids.ids})' if self.production_ids else ''}
            order by stt
        """
        return query_final

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Utility = self.env['res.utility']
        query = self._get_query()
        data = Utility.execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo quyết toán lệnh sản xuất')
        sheet.set_row(0, 30)
        sheet.set_row(4, 30)
        sheet.write(0, 0, 'Báo cáo quyết toán lệnh sản xuất', formats.get('header_format'))
        sheet.write(2, 0, 'Ngày: %s' % self.date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(TITLES) - 1, 20)
        row = 5
        for value in data['data']:
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ma_lenh_sx'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('kho_xuong'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ma_vat_tu'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('sl_sx_ke_hoach'), formats.get('int_number_format'))
            sheet.write(row, 5, value.get('sl_nk_thuc_te'), formats.get('int_number_format'))
            sheet.write(row, 6, value.get('sl_th_thuc_te'), formats.get('int_number_format'))
            sheet.write(row, 7, value.get('sl_vt_kho_cap'), formats.get('int_number_format'))
            sheet.write(row, 8, value.get('chenh_lech_qt'), formats.get('int_number_format'))
            row += 1
