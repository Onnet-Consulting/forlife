# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import xlsxwriter
import copy
import io


class ReportBase(models.AbstractModel):
    _name = 'report.base'
    _description = 'Report Base'

    def print_xlsx(self):
        return {
            'type': 'ir.actions.act_url',
            'name': self._description,
            'url': '/custom/download/xlsx/%s/%s/%d' % (self._description, self._name, self.id),
            'target': 'self'
        }

    def view_report(self):
        ...

    def generate_xlsx_report(self, workbook):
        ...

    def get_xlsx(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        self.generate_xlsx_report(workbook)
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        return generated_file

    def get_format_workbook(self, workbook):
        header_format = {
            'bold': 1,
            'size': 20
        }
        title_format = {
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#dbeef4'
        }
        normal_format = {
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        }
        datetime_format = {
            'num_format': "dd/mm/yy hh:mm:ss",
        }
        datetime_format.update(normal_format)
        float_number_format = {}
        center_format = copy.copy(normal_format)
        int_number_format = {}

        center_format.update({'align': 'center'})
        float_number_format.update(normal_format)
        int_number_format.update(normal_format)
        float_number_title_format = float_number_format.copy()
        float_number_title_format.update(title_format)
        int_number_title_format = int_number_format.copy()
        int_number_title_format.update(title_format)

        title_format = workbook.add_format(title_format)
        datetime_format = workbook.add_format(datetime_format)
        normal_format = workbook.add_format(normal_format)
        center_format = workbook.add_format(center_format)
        header_format = workbook.add_format(header_format)

        float_number_format = workbook.add_format(float_number_format)
        float_number_format.set_num_format('#,##0.00')
        int_number_format = workbook.add_format(int_number_format)
        int_number_format.set_num_format('#,##0')

        float_number_title_format = workbook.add_format(float_number_title_format)
        float_number_title_format.set_num_format('#,##0.00')
        int_number_title_format = workbook.add_format(int_number_title_format)
        int_number_title_format.set_num_format('#,##0')

        return {
            'header_format': header_format,
            'title_format': title_format,
            'datetime_format': datetime_format,
            'normal_format': normal_format,
            'center_format': center_format,
            'float_number_format': float_number_format,
            'int_number_format': int_number_format,
            'float_number_title_format': float_number_title_format,
            'int_number_title_format': int_number_title_format,
        }
