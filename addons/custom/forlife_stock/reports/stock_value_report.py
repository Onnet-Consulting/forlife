# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from datetime import datetime
import pytz
from ..tools import convert_to_utc_datetime
from ..excel_style import get_style
import base64
from io import BytesIO
from xlsxwriter.workbook import Workbook


def read_sql_file(file_path):
    fd = tools.file_open(file_path, 'r')
    sqlFile = fd.read()
    fd.close()
    return sqlFile


class StockValueReport(models.TransientModel):
    _name = 'stock.value.report'
    _description = 'Stock Value Report'

    date_from = fields.Date('From Date', required=True)
    date_to = fields.Date('To Date', default=fields.Date.context_today, required=True)
    detail_ids = fields.One2many('stock.value.report.detail', 'report_id', 'Detail')

    # file sql
    def init(self):
        outgoing_value_diff_report = read_sql_file('./forlife_stock/sql_functions/outgoing_value_diff_report.sql')
        outgoing_value_diff_picking_type_report = read_sql_file(
            './forlife_stock/sql_functions/outgoing_value_diff_picking_type_report.sql')
        stock_incoming_outgoing_report = read_sql_file(
            './forlife_stock/sql_functions/stock_incoming_outgoing_report.sql')
        self.env.cr.execute(outgoing_value_diff_report)
        self.env.cr.execute(outgoing_value_diff_picking_type_report)
        self.env.cr.execute(stock_incoming_outgoing_report)

    def action_download_excel(self, data, name):
        vals = {
            'name': f'{name}.xlsx',
            'datas': data,
            'type': 'binary',
            # 'res_model': self._name,
            # 'res_id': self.id,
        }
        file_xls = self.env['ir.attachment'].create(vals)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(file_xls.id) + '?download=true',
            'target': 'new',
        }

    def action_get_outgoing_value_diff_report(self):
        # must be utc time
        current_tz = pytz.timezone(self.env.context.get('tz'))
        utc_datetime_from = convert_to_utc_datetime(current_tz, str(self.date_from) + " 00:00:00")
        utc_datetime_to = convert_to_utc_datetime(current_tz, str(self.date_to) + " 23:59:59")
        self._cr.execute("""
            DELETE FROM stock_value_report_detail WHERE create_uid = %s and report_id = %s;
            INSERT INTO stock_value_report_detail (
                                        report_id,
                                        currency_id,
                                        product_id,
                                        opening_quantity,
                                        opening_value,
                                        incoming_quantity,
                                        incoming_value,
                                        odoo_outgoing_quantity,
                                        odoo_outgoing_value,
                                        real_outgoing_price_unit,
                                        real_outgoing_value,
                                        create_date,
                                        write_date,
                                        create_uid,
                                        write_uid)
            SELECT %s,
                    %s,
                    product_id,
                    opening_quantity,
                    opening_value,
                    incoming_quantity,
                    incoming_value,
                    odoo_outgoing_quantity,
                    odoo_outgoing_value,
                    real_outgoing_price_unit,
                    real_outgoing_value,
                    %s,
                    %s,
                    %s,
                    %s
            FROM outgoing_value_diff_report(%s, %s, %s)
        """, (self.env.user.id, self.id, self.id, self.env.company.currency_id.id, datetime.utcnow(), datetime.utcnow(),
              self.env.user.id,
              self.env.user.id, utc_datetime_from, utc_datetime_to, self.env.company.id))

    def action_export_outgoing_value_diff_report(self):
        # define function
        def get_data():
            # must be utc time
            current_tz = pytz.timezone(self.env.context.get('tz'))
            utc_datetime_from = convert_to_utc_datetime(current_tz, str(self.date_from) + " 00:00:00")
            utc_datetime_to = convert_to_utc_datetime(current_tz, str(self.date_to) + " 23:59:59")
            self._cr.execute("""
                        SELECT pp.default_code,
                                pt.name,
                                report.opening_quantity,
                                report.opening_value,
                                report.incoming_quantity,
                                report.incoming_value,
                                report.odoo_outgoing_quantity,
                                report.odoo_outgoing_value,
                                report.real_outgoing_price_unit,
                                report.real_outgoing_value
                        FROM outgoing_value_diff_report(%s, %s, %s) as report
                        LEFT JOIN product_product pp ON pp.id = report.product_id
                        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id""",
                             (utc_datetime_from, utc_datetime_to, self.env.company.id))
            return self._cr.dictfetchall()

        def write_header(wssheet):
            # --------------------------------------Title---------------------------------------------------
            wssheet.merge_range("A1:L1", _('Outgoing Value Different Report'), style_excel['style_title'])
            wssheet.write("D3", 'Kỳ báo cáo', style_excel['style_header_bold'])
            wssheet.write("E3", f'Từ ngày: {self.date_from.strftime("%d/%m/%Y")}',
                          style_excel['style_left_data_string'])
            wssheet.write("F3", f'Đến ngày: {self.date_to.strftime("%d/%m/%Y")}',
                          style_excel['style_left_data_string'])
            # --------------------------------------Header---------------------------------------------------

            wssheet.write("E4", '(Ngày hạch toán trên phiếu)', style_excel['style_header_unbold'])
            wssheet.write("F4", '(Ngày hạch toán trên phiếu)', style_excel['style_header_unbold'])

            # --------------------------------------Header Table----------------------------------------------
            wssheet.merge_range("A7:A8", 'STT', style_excel['style_header_bold_border'])
            wssheet.merge_range("B7:B8", 'Mã sản phẩm', style_excel['style_header_bold_border'])
            wssheet.merge_range("C7:C8", 'Tên sản phẩm', style_excel['style_header_bold_border'])
            wssheet.merge_range("D7:E7", 'Tồn đầu kỳ', style_excel['style_header_bold_border'])
            wssheet.merge_range("F7:G7", 'Nhập kho', style_excel['style_header_bold_border'])
            wssheet.merge_range("H7:I7", 'Xuất kho Odoo (BQ từng lần)', style_excel['style_header_bold_border'])
            wssheet.merge_range("J7:K7", 'Giá trị xuất kho update (BQ cuối kỳ)',
                                style_excel['style_header_bold_border'])
            wssheet.merge_range("L7:L8", 'Tổng giá trị chênh lệch trong kỳ', style_excel['style_header_bold_border'])
            wssheet.write("D8", 'Số lượng', style_excel['style_header_bold_border'])
            wssheet.write("E8", 'Giá trị', style_excel['style_header_bold_border'])
            wssheet.write("F8", 'Số lượng', style_excel['style_header_bold_border'])
            wssheet.write("G8", 'Giá trị', style_excel['style_header_bold_border'])
            wssheet.write("H8", 'Số lượng', style_excel['style_header_bold_border'])
            wssheet.write("I8", 'Giá trị', style_excel['style_header_bold_border'])
            wssheet.write("J8", 'Đơn giá', style_excel['style_header_bold_border'])
            wssheet.write("K8", 'Số lượng', style_excel['style_header_bold_border'])

        def write_detail_table(wssheet, result):
            def get_number_data(result_dict, name):
                return result_dict.get(name, 0) if int(item.get(name, 0)) != 0 else ''

            row = 8
            total_opening_quantity = 0
            total_opening_value = 0
            total_incoming_quantity = 0
            total_incoming_value = 0
            total_odoo_outgoing_quantity = 0
            total_odoo_outgoing_value = 0
            total_real_outgoing_value = 0
            total_diff_outgoing_value = 0
            for index, item in enumerate(result):
                opening_quantity = item.get('opening_quantity', 0)
                opening_value = item.get('opening_value', 0)
                incoming_value = item.get('incoming_value', 0)
                incoming_quantity = item.get('incoming_quantity', 0)
                odoo_outgoing_quantity = item.get('odoo_outgoing_quantity', 0)
                odoo_outgoing_value = item.get('odoo_outgoing_quantity', 0)
                real_outgoing_price_unit = item.get('real_outgoing_price_unit', 0)
                real_outgoing_value = item.get('real_outgoing_value', 0)
                wssheet.write(row, 0, index + 1, style_excel['style_right_data_int'])
                wssheet.write(row, 1, item.get('default_code', ''), style_excel['style_left_data_string_border'])
                wssheet.write(row, 2,
                              item.get('name', {}).get(self.env.context.get('lang')) if item.get('name', {}).get(
                                  self.env.context.get('lang')) else item.get('name', {}).get('en_US'),
                              style_excel['style_left_data_string_border'])
                wssheet.write(row, 3, opening_quantity, style_excel['style_right_data_float'])
                wssheet.write(row, 4, opening_value, style_excel['style_right_data_float'])
                wssheet.write(row, 5, incoming_quantity, style_excel['style_right_data_float'])
                wssheet.write(row, 6, incoming_value, style_excel['style_right_data_float'])
                wssheet.write(row, 7, odoo_outgoing_quantity, style_excel['style_right_data_float'])
                wssheet.write(row, 8, odoo_outgoing_value, style_excel['style_right_data_float'])
                wssheet.write(row, 9, real_outgoing_price_unit, style_excel['style_right_data_float'])
                wssheet.write(row, 10, real_outgoing_value, style_excel['style_right_data_float'])
                wssheet.write(row, 11, odoo_outgoing_value - real_outgoing_value, style_excel['style_right_data_float'])

                total_opening_quantity += opening_quantity
                total_opening_value += opening_value
                total_incoming_quantity += incoming_quantity
                total_incoming_value += incoming_value
                total_odoo_outgoing_quantity += odoo_outgoing_quantity
                total_odoo_outgoing_value += odoo_outgoing_value
                total_real_outgoing_value += real_outgoing_value
                total_diff_outgoing_value += odoo_outgoing_value - real_outgoing_value

                row += 1
            # Sum
            wssheet.merge_range(row, 0, row, 2, "Tổng cộng", style_excel['style_header_bold_border'])
            wssheet.write(row, 3, total_opening_quantity if total_opening_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 4, total_opening_value if total_opening_value != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 5, total_incoming_quantity if total_incoming_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 6, total_incoming_quantity if total_incoming_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 7, total_odoo_outgoing_quantity if total_odoo_outgoing_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 8, total_odoo_outgoing_value if total_odoo_outgoing_value != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 9, '', style_excel['style_right_data_float'])
            wssheet.write(row, 10, total_real_outgoing_value if total_real_outgoing_value != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 11, total_diff_outgoing_value if total_diff_outgoing_value != 0 else '',
                          style_excel['style_right_data_float'])

            return row

        def write_footer(wssheet, last_row):
            # --------------------------------------Footer---------------------------------------------------
            wssheet.merge_range(last_row + 2, 7, last_row + 2, 11, 'Ngày.....tháng.....năm.....',
                                style_excel['style_header_unbold'])
            wssheet.merge_range(last_row + 3, 7, last_row + 3, 11, 'Người lập phiếu',
                                style_excel['style_header_bold'])
            wssheet.merge_range(last_row + 4, 7, last_row + 4, 11, '(Kí ghi rõ họ tên)',
                                style_excel['style_header_unbold'])

            wssheet.merge_range(last_row + 3, 0, last_row + 3, 3, 'Thủ kho',
                                style_excel['style_header_bold'])
            wssheet.merge_range(last_row + 4, 0, last_row + 4, 3, '(Kí ghi rõ họ tên)',
                                style_excel['style_header_unbold'])

        # true action
        result = get_data()

        # write data to excel
        buf = BytesIO()
        wb = Workbook(buf)
        style_excel = get_style(wb)
        wssheet = wb.add_worksheet('Report')

        # --------------------------------------Header----------------------------------------------------
        write_header(wssheet)
        # --------------------------------------Detail Table----------------------------------------------
        last_row = write_detail_table(wssheet, result)
        # --------------------------------------Footer----------------------------------------------
        write_footer(wssheet, last_row)

        wb.close()
        buf.seek(0)
        xlsx_data = buf.getvalue()

        return self.action_download_excel(base64.encodebytes(xlsx_data), _('Outgoing Value Different Report'))

    def action_get_stock_incoming_outgoing_report(self):
        # must be utc time
        current_tz = pytz.timezone(self.env.context.get('tz'))
        utc_datetime_from = convert_to_utc_datetime(current_tz, str(self.date_from) + " 00:00:00")
        utc_datetime_to = convert_to_utc_datetime(current_tz, str(self.date_to) + " 23:59:59")
        self._cr.execute("""
            DELETE FROM stock_value_report_detail WHERE create_uid = %s and report_id = %s;
            INSERT INTO stock_value_report_detail (
                                        report_id,
                                        currency_id,
                                        product_id,
                                        opening_quantity,
                                        opening_value,
                                        incoming_quantity,
                                        incoming_value,
                                        odoo_outgoing_quantity,
                                        real_outgoing_value,
                                        closing_quantity,
                                        closing_value,
                                        create_date,
                                        write_date,
                                        create_uid,
                                        write_uid)
            SELECT %s,
                    %s,
                    product_id,
                    opening_quantity,
                    opening_value,
                    incoming_quantity,
                    incoming_value,
                    odoo_outgoing_quantity,
                    real_outgoing_value,
                    closing_quantity,
                    closing_value,
                    %s,
                    %s,
                    %s,
                    %s
            FROM stock_incoming_outgoing_report(%s, %s, %s)
        """, (self.env.user.id, self.id, self.id, self.env.company.currency_id.id, datetime.utcnow(), datetime.utcnow(),
              self.env.user.id,
              self.env.user.id, utc_datetime_from, utc_datetime_to, self.env.company.id))

    def action_export_stock_incoming_outgoing_report(self):
        # define function
        def get_data():
            # must be utc time
            current_tz = pytz.timezone(self.env.context.get('tz'))
            utc_datetime_from = convert_to_utc_datetime(current_tz, str(self.date_from) + " 00:00:00")
            utc_datetime_to = convert_to_utc_datetime(current_tz, str(self.date_to) + " 23:59:59")
            self._cr.execute("""
                                SELECT pp.default_code,
                                        pt.name,
                                        report.opening_quantity,
                                        report.opening_value,
                                        report.incoming_quantity,
                                        report.incoming_value,
                                        report.odoo_outgoing_quantity,
                                        report.real_outgoing_value,
                                        report.closing_quantity,
                                        report.closing_value
                                FROM stock_incoming_outgoing_report(%s, %s, %s) as report
                                LEFT JOIN product_product pp ON pp.id = report.product_id
                                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id""",
                             (utc_datetime_from, utc_datetime_to, self.env.company.id))
            return self._cr.dictfetchall()

        def write_header(wssheet):
            # --------------------------------------Title---------------------------------------------------
            wssheet.merge_range("A1:L1", _('Stock Incoming Outgoing Report'), style_excel['style_title'])
            wssheet.write("D3", 'Kỳ báo cáo', style_excel['style_header_bold'])
            wssheet.write("E3", f'Từ ngày: {self.date_from.strftime("%d/%m/%Y")}',
                          style_excel['style_left_data_string'])
            wssheet.write("F3", f'Đến ngày: {self.date_to.strftime("%d/%m/%Y")}',
                          style_excel['style_left_data_string'])
            # --------------------------------------Header---------------------------------------------------

            wssheet.write("E4", '(Ngày hạch toán trên phiếu)', style_excel['style_header_unbold'])
            wssheet.write("F4", '(Ngày hạch toán trên phiếu)', style_excel['style_header_unbold'])

            # --------------------------------------Header Table----------------------------------------------
            wssheet.merge_range("A7:A8", 'STT', style_excel['style_header_bold_border'])
            wssheet.merge_range("B7:B8", 'Mã sản phẩm', style_excel['style_header_bold_border'])
            wssheet.merge_range("C7:C8", 'Tên sản phẩm', style_excel['style_header_bold_border'])
            wssheet.merge_range("D7:E7", 'Tồn đầu kỳ', style_excel['style_header_bold_border'])
            wssheet.merge_range("F7:G7", 'Nhập kho', style_excel['style_header_bold_border'])
            wssheet.merge_range("H7:I7", 'Xuất kho', style_excel['style_header_bold_border'])
            wssheet.merge_range("J7:K7", 'Tồn cuối kỳ',
                                style_excel['style_header_bold_border'])
            wssheet.merge_range("L7:L8", 'Ghi chú', style_excel['style_header_bold_border'])
            wssheet.write("D8", 'Số lượng', style_excel['style_header_bold_border'])
            wssheet.write("E8", 'Giá trị', style_excel['style_header_bold_border'])
            wssheet.write("F8", 'Số lượng', style_excel['style_header_bold_border'])
            wssheet.write("G8", 'Giá trị', style_excel['style_header_bold_border'])
            wssheet.write("H8", 'Số lượng', style_excel['style_header_bold_border'])
            wssheet.write("I8", 'Giá trị', style_excel['style_header_bold_border'])
            wssheet.write("J8", 'Số lượng', style_excel['style_header_bold_border'])
            wssheet.write("K8", 'Số lượng', style_excel['style_header_bold_border'])

        def write_detail_table(wssheet, result):
            def get_number_data(result_dict, name):
                return result_dict.get(name, 0) if int(item.get(name, 0)) != 0 else ''

            row = 8
            total_opening_quantity = 0
            total_opening_value = 0
            total_incoming_quantity = 0
            total_incoming_value = 0
            total_odoo_outgoing_quantity = 0
            total_real_outgoing_value = 0
            total_closing_quantity = 0
            total_closing_value = 0
            for index, item in enumerate(result):
                opening_quantity = item.get('opening_quantity', 0)
                opening_value = item.get('opening_value', 0)
                incoming_value = item.get('incoming_value', 0)
                incoming_quantity = item.get('incoming_quantity', 0)
                odoo_outgoing_quantity = item.get('odoo_outgoing_quantity', 0)
                real_outgoing_value = item.get('real_outgoing_value', 0)
                closing_quantity = item.get('closing_quantity', 0)
                closing_value = item.get('closing_value', 0)
                wssheet.write(row, 0, index + 1, style_excel['style_right_data_int'])
                wssheet.write(row, 1, item.get('default_code', ''), style_excel['style_left_data_string_border'])
                wssheet.write(row, 2,
                              item.get('name', {}).get(self.env.context.get('lang')) if item.get('name', {}).get(
                                  self.env.context.get('lang')) else item.get('name', {}).get('en_US'),
                              style_excel['style_left_data_string_border'])
                wssheet.write(row, 3, opening_quantity, style_excel['style_right_data_float'])
                wssheet.write(row, 4, opening_value, style_excel['style_right_data_float'])
                wssheet.write(row, 5, incoming_quantity, style_excel['style_right_data_float'])
                wssheet.write(row, 6, incoming_value, style_excel['style_right_data_float'])
                wssheet.write(row, 7, odoo_outgoing_quantity, style_excel['style_right_data_float'])
                wssheet.write(row, 8, real_outgoing_value, style_excel['style_right_data_float'])
                wssheet.write(row, 9, closing_quantity, style_excel['style_right_data_float'])
                wssheet.write(row, 10, closing_value, style_excel['style_right_data_float'])
                wssheet.write(row, 11, '', style_excel['style_right_data_float'])

                total_opening_quantity += opening_quantity
                total_opening_value += opening_value
                total_incoming_quantity += incoming_quantity
                total_incoming_value += incoming_value
                total_odoo_outgoing_quantity += odoo_outgoing_quantity
                total_real_outgoing_value += real_outgoing_value
                total_closing_quantity += closing_quantity
                total_closing_value += closing_value

                row += 1
            # Sum
            wssheet.merge_range(row, 0, row, 2, "Tổng cộng", style_excel['style_header_bold_border'])
            wssheet.write(row, 3, total_opening_quantity if total_opening_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 4, total_opening_value if total_opening_value != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 5, total_incoming_quantity if total_incoming_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 6, total_incoming_quantity if total_incoming_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 7, total_odoo_outgoing_quantity if total_odoo_outgoing_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 8, total_real_outgoing_value if total_real_outgoing_value != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 9, total_closing_quantity if total_closing_quantity != 0 else '',
                          style_excel['style_right_data_float'])
            wssheet.write(row, 10, total_closing_value if total_closing_value != 0 else '',
                          style_excel['style_right_data_float'])

            return row

        def write_footer(wssheet, last_row):
            # --------------------------------------Footer---------------------------------------------------
            wssheet.merge_range(last_row + 2, 7, last_row + 2, 11, 'Ngày.....tháng.....năm.....',
                                style_excel['style_header_unbold'])
            wssheet.merge_range(last_row + 3, 7, last_row + 3, 11, 'Người lập phiếu',
                                style_excel['style_header_bold'])
            wssheet.merge_range(last_row + 4, 7, last_row + 4, 11, '(Kí ghi rõ họ tên)',
                                style_excel['style_header_unbold'])

            wssheet.merge_range(last_row + 3, 0, last_row + 3, 3, 'Thủ kho',
                                style_excel['style_header_bold'])
            wssheet.merge_range(last_row + 4, 0, last_row + 4, 3, '(Kí ghi rõ họ tên)',
                                style_excel['style_header_unbold'])

        # true action
        result = get_data()

        # write data to excel
        buf = BytesIO()
        wb = Workbook(buf)
        style_excel = get_style(wb)
        wssheet = wb.add_worksheet('Report')

        # --------------------------------------Header----------------------------------------------------
        write_header(wssheet)
        # --------------------------------------Detail Table----------------------------------------------
        last_row = write_detail_table(wssheet, result)
        # --------------------------------------Footer----------------------------------------------
        write_footer(wssheet, last_row)

        wb.close()
        buf.seek(0)
        xlsx_data = buf.getvalue()

        return self.action_download_excel(base64.encodebytes(xlsx_data), _('Stock Incoming Outgoing Report'))

    def action_export_outgoing_value_diff_picking_type_report(self):
        pass
