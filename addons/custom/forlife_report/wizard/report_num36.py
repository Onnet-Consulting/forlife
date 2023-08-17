# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT',
    'Lệnh sản xuất',
    'Quản lý đơn hàng',
    'Đơn vị gia công/xưởng sản xuất',
    'Mã thành phẩm',
    'Đơn vị tính',
    'Số lượng sản xuất kế hoạch',
    'Số lượng đã nhập kho',
    'Số lượng còn lại',
]


class ReportNum36(models.TransientModel):
    _name = 'report.num36'
    _inherit = ['report.base', 'export.excel.client']
    _description = 'Nhập kho thành phẩm sản xuất'

    produce_id = fields.Many2many('forlife.production', string='Lệnh sản xuất')
    from_date = fields.Date(string='Từ ngày')
    to_date = fields.Date(string='Đến ngày')

    @api.constrains('produce_id', 'from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if (not record.from_date and not record.to_date) and not record.produce_id:
                raise ValidationError(_('Vui lòng chọn khoảng thời gian hoặc lệnh sản xuất!.'))

    def _get_query(self, allowed_company):
        self.ensure_one()
        tz_offset = self.tz_offset
        user_lang_code = self.env.user.lang

        query = f"""
            select
                fp.code as lsx,
                he.name as ql_donhang,
                case
                    when fp.production_department = 'tu_san_xuat'
                    and fp.machining_id is null then coalesce (aaa2.name->>'vi_VN', aaa2.name->>'en_US')
                    else coalesce (aaa.name->>'vi_VN', aaa.name->>'en_US')
                end as dv_giacong,
                coalesce (pt.name ->> 'vi_VN', pt.name ->> 'en_US') as ma_thanhpham,
                coalesce (uu.name->>'vi_VN',
                uu.name->>'en_US') as dvt,
                fpfp.produce_qty as sl_sanxuat,
                fpfp.stock_qty as sl_nhapkho,
                fpfp.remaining_qty as sl_conlai
            from
                forlife_production fp
            join forlife_production_finished_product fpfp on
                fp.id = fpfp.forlife_production_id
            left join account_analytic_account aaa on
                fp.machining_id = aaa.id
            left join account_analytic_account aaa2 on
                fp.implementation_id = aaa2.id
            left join hr_employee he on
                fp.leader_id = he.id
            join product_product pp on
                fpfp.product_id = pp.id
            join product_template pt on
                pp.product_tmpl_id = pt.id
            left join uom_uom uu on
                pt.uom_id = uu.id
            where fp.active is true
        """
        if self.produce_id:
            query += f" and fp.id = any(array{self.produce_id.ids})"
        if self.from_date and self.to_date:
            query += f" and {format_date_query('fp.created_date', tz_offset)} between '{self.from_date}' and '{self.to_date}'"
        query += f"""order by fp.code;"""
        return query

    def handle_data(self, data):
        data_dict = {}
        for d in data:
            if d['lsx'] in data_dict:
                data_dict[d['lsx']] += [d]
            else:
                data_dict[d['lsx']] = [d]
        result = []
        for key, values in data_dict.items():
            count = 0
            for v in values:
                if key == v['lsx'] and count == 0:
                    result += [v]
                else:
                    result += [{
                        'lsx': '',
                        'ql_donhang': '',
                        'dv_giacong': '',
                        'ma_thanhpham': v['ma_thanhpham'],
                        'dvt': v['dvt'],
                        'sl_sanxuat': v['sl_sanxuat'],
                        'sl_nhapkho': v['sl_nhapkho'],
                        'sl_conlai': v['sl_conlai'],
                    }]
                count = 1
        return result

    def get_data(self, allowed_company):
        allowed_company = allowed_company or [-1]
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query(allowed_company)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        data = self.handle_data(data)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo nhập kho thành phẩm sản xuất')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo nhập kho thành phẩm sản xuất', formats.get('header_format'))
        sheet.write(2, 0, 'Lệnh sản xuất: %s' % self.produce_id.mapped('name'), formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày: %s đến ngày: %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(TITLES):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        index = 0
        for value in data['data']:
            if value.get('lsx'):
                index += 1
                sheet.write(row, 0, index, formats.get('center_format'))
            else:
                sheet.write(row, 0, '', formats.get('center_format'))
            sheet.write(row, 1, value.get('lsx'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ql_donhang'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('dv_giacong'), formats.get('center_format'))
            sheet.write(row, 4, value.get('ma_thanhpham'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('dvt'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('sl_sanxuat'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('sl_nhapkho'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('sl_conlai'), formats.get('normal_format'))
            row += 1
