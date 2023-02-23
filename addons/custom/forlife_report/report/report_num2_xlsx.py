# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

HEADER = ['Mã SP', 'Tên SP', 'Tồn']


class Num2ReportXlsx(models.AbstractModel):
    _name = "report.forlife_report.report_num2_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Num2 Report"

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
        sheet.set_column(0, len(HEADER), 24)
        for i, val in enumerate(HEADER):
            sheet.write(0, i, val, _format_header)
        row = 1
        for value in data['product_data']:
            sheet.write(row, 0, value['product_barcode'], _format_normal)
            sheet.write(row, 1, value['product_name'], _format_normal)
            sheet.write(row, 2, value['quantity'], _format_number0)
            row += 1
