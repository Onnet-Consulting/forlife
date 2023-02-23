# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

HEADER = ['STT', 'Mã SP', 'Tên SP', 'Đơn vị', 'Giá', 'Số lượng', 'Chiết khấu', 'Thành tiền', 'Thành tiền có thuế']


class Num1ReportXlsx(models.AbstractModel):
    _name = "report.forlife_report.report_num1_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Num1 Report"

    def generate_xlsx_report(self, workbook, data, record):
        data = record[0].get_data()
        sheet = workbook.add_worksheet(record._description)
        _format_header = workbook.add_format({
            'bold': True,
            'bg_color': '#a8cde3',
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
        })
        _format_number0 = workbook.add_format({
            'align': 'center',
        })
        _format_number2 = workbook.add_format({
            'align': 'right',
            'num_format': '#,##0.00',
        })
        _format_normal = workbook.add_format({
            'text_wrap': True,
        })
        sheet.set_row(0, 25)
        sheet.set_column(1, len(HEADER) - 1, 24)
        for i, val in enumerate(HEADER):
            sheet.write(0, i, val, _format_header)
        row = 1
        for value in data:
            sheet.write(row, 0, value['num'], _format_number0)
            sheet.write(row, 1, value['product_barcode'], _format_normal)
            sheet.write(row, 2, value['product_name'], _format_normal)
            sheet.write(row, 3, value['uom_name'], _format_normal)
            sheet.write(row, 4, value['price_unit'], _format_number2)
            sheet.write(row, 5, value['qty'], _format_number0)
            sheet.write(row, 6, value['discount_percent'], _format_number2)
            sheet.write(row, 7, value['amount_without_tax'], _format_number2)
            sheet.write(row, 8, value['amount_with_tax'], _format_number2)
            row += 1
