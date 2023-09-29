# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import calendar


class ReportNum47(models.TransientModel):
    _name = 'report.num47'
    _inherit = 'report.base'
    _description = 'Bảng kê Doanh thu'

    @api.model
    def _get_default_year(self):
        return fields.Date.today().year

    @api.model
    def _get_default_month(self):
        return self.env['month.data'].search([('code', '=', str(fields.Date.today().month))])

    month = fields.Many2one('month.data', 'Month', required=True, default=_get_default_month)
    year = fields.Integer('Year', required=True, default=_get_default_year)
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    store_id = fields.Many2one('store', string='Store', required=True)

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_id = False

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        user_lang_code = self.env.user.lang
        time = "%.2d/%.4d" % (int(self.month.code), self.year)
        sql = f"""
with orders as (select po.id,
                       (date_order + interval '{tz_offset} h')::date as date,
                       po.session_id,
                       amount_paid
                from pos_order po
                         join pos_session ps on po.session_id = ps.id
                         join pos_config pc on ps.config_id = pc.id
                where to_char(po.date_order + interval '{tz_offset} h', 'MM/YYYY') = '{time}'
                  and po.brand_id = {self.brand_id.id}
                  and pc.store_id = {self.store_id.id if self.store_id else -1}),
     amount_by_payment_method as (select to_char(pp.payment_date + interval '{tz_offset} h', 'DD')                  as date,
                                         pp.payment_method_id,
                                         coalesce(ppm.name::json ->> '{user_lang_code}', ppm.name::json ->> 'en_US') as payment_method,
                                         sum(pp.amount)                                                   as amount_total
                                  from pos_payment pp
                                           join pos_payment_method ppm on pp.payment_method_id = ppm.id
                                  where pp.pos_order_id in (select distinct id from orders)
                                  group by to_char(pp.payment_date + interval '{tz_offset} h', 'DD'), pp.payment_method_id,
                                           coalesce(ppm.name::json ->> '{user_lang_code}', ppm.name::json ->> 'en_US')),
     pos_amount_paid as (select to_char(date + interval '{tz_offset} h', 'DD') as date,
                                sum(amount_paid)                     as amount_total
                         from orders
                         group by date),
     expenses as (select to_char(create_date + interval '{tz_offset} h', 'DD') as date,
                         sum(amount)                                           as amount_total
                  from account_bank_statement_line
                  where pos_session_id in (select distinct session_id from orders)
                    and to_char(create_date + interval '{tz_offset} h', 'MM/YYYY') = '{time}'
                  group by to_char(create_date + interval '{tz_offset} h', 'DD'))
select (select json_object_agg(date, detail)
        from (select date, json_object_agg(payment_method_id, amount_total) as detail
              from amount_by_payment_method
              group by date) as s1)                                                                   as amount_payment_methods,
       (select json_object_agg(date, amount_total) from pos_amount_paid)                              as pos_amount_paid,
       (select json_object_agg(payment_method_id, payment_method)
        from (select distinct payment_method_id, payment_method from amount_by_payment_method) as s2) as payment_methods,
       (select json_object_agg(date, amount_total) from expenses)                                     as expenses
"""
        return sql

    @api.model
    def format_data(self, data):
        amount_payment_methods = data[0].get('amount_payment_methods') or {}
        pos_amount_paid = data[0].get('pos_amount_paid') or {}
        payment_methods = data[0].get('payment_methods') or {}
        expenses = data[0].get('expenses') or {}
        num_of_days = calendar.monthrange(self.year, int(self.month.code))[1]
        res = []
        payment_method_ids = list(payment_methods.keys())
        for num in range(1, num_of_days + 1):
            day = '%.2d' % num
            x_thanh_toan = amount_payment_methods.get(day) or {}
            thanh_toan = [(x_thanh_toan.get(x) or 0) for x in payment_method_ids]
            chi_phi = expenses.get(day) or 0
            dt_tong = pos_amount_paid.get(day) or 0
            tong_tt = sum(thanh_toan)
            chenh_lech = dt_tong - tong_tt - chi_phi
            if chenh_lech > 0:
                ghi_chu = 'Cửa hàng đang nộp thiếu doanh thu'
            elif chenh_lech < 0:
                ghi_chu = 'Cửa hàng đang nộp thừa doanh thu'
            else:
                ghi_chu = 'Doanh thu khớp' if any([dt_tong, tong_tt, chi_phi]) else ''
            res.append({
                'ngay': f'Ngày {day}',
                'dt_tong': dt_tong,
                'thanh_toan': thanh_toan,
                'chi_phi': chi_phi,
                'chenh_lech': chenh_lech,
                'ghi_chu': ghi_chu,
            })
        return {
            'titles': ['Ngày', 'Tổng doanh thu'] + [payment_methods.get(x) for x in payment_method_ids] + ['Chi phí', 'Chênh lệch', 'Ghi chú'],
            'data': res,
            'column_add': len(payment_method_ids),
        }

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        result = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        res = dict(self.format_data(result))
        values.update(res)
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Bảng kê Doanh thu')
        sheet.set_row(0, 25)
        sheet.set_row(4, 25)
        sheet.freeze_panes(5, 0)
        sheet.merge_range(0, 0, 0, len(data.get('titles')) - 1, 'Bảng kê Doanh thu', formats.get('header_format'))
        sheet.merge_range(1, 0, 1, len(data.get('titles')) - 1, "Tháng %.2d/%.4d" % (int(self.month.code), self.year), formats.get('italic_format'))
        sheet.merge_range(2, 0, 2, len(data.get('titles')) - 1, f"Cửa hàng: {self.store_id.name}", formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(data.get('titles')) - 1, 20)
        row = 5
        for value in data.get('data'):
            i = -1
            sheet.write(row, 0, value.get('ngay'), formats.get('center_format'))
            sheet.write(row, 1, value.get('dt_tong'), formats.get('int_number_format'))
            for i in range(0, data.get('column_add')):
                sheet.write(row, i + 2, value.get('thanh_toan')[i], formats.get('int_number_format'))
            sheet.write(row, i + 3, value.get('chi_phi'), formats.get('int_number_format'))
            sheet.write(row, i + 4, value.get('chenh_lech'), formats.get('int_number_format'))
            sheet.write(row, i + 5, value.get('ghi_chu'), formats.get('normal_format'))
            row += 1

    @api.model
    def get_format_workbook(self, workbook):
        res = dict(super().get_format_workbook(workbook))
        res.get('header_format').set_align('center')
        res.get('italic_format').set_align('center')
        return res
