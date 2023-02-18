# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class NPSReportXlsx(models.AbstractModel):
    _name = "report.forlife_net_promoter_score.net_promoter_score_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "NPS Report"

    def generate_xlsx_report(self, workbook, data, record):
        if not record:
            raise ValidationError(_('NPS Report values not found.'))
        result = record[0].filter_data([])
        sheet = workbook.add_worksheet("NPS Report")
        _format_header = workbook.add_format({
            'bold': True,
            'bg_color': '#a8cde3',
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
        })
        _format_center = workbook.add_format({
            'align': 'center',
            'text_wrap': True,
        })
        _format_normal = workbook.add_format({
            'text_wrap': True,
        })
        sheet.set_row(0, 25)
        sheet.set_column(1, len(result[0]) - 1, 20)
        row = 0
        for value in result:
            if row == 0:
                for i, val in enumerate(value):
                    sheet.write(row, i, val, _format_header)
            else:
                for i, val in enumerate(value):
                    if i in (0, 7, 8, 9, 11):
                        sheet.write(row, i, val, _format_center)
                    else:
                        sheet.write(row, i, val, _format_normal)
            row += 1
