# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import xlsxwriter
import copy
import io


class ReportBase(models.AbstractModel):
    _name = 'report.base'
    _description = 'Report Base'

    def print_xlsx(self):
        filename = self.get_filename_standardized(self.get_filename())
        return {
            'type': 'ir.actions.act_url',
            'name': self._description,
            'url': '/custom/download/xlsx/%s/%s/%d/%s' % (filename, self._name, self.id, self._context.get('allowed_company_ids', [])),
            'target': 'current'

        }

    @api.model
    def get_filename_standardized(self, filename):
        ky_tu_db_excel = '\\/:*?"<>|.'
        ky_tu_db_url = '%!#$&\'()+,'
        for c in ky_tu_db_url:
            filename = filename.replace(c, '')
        for c in ky_tu_db_excel:
            filename = filename.replace(c, '_')
        return filename

    def get_filename(self):
        return self._description or self._name

    def view_report(self):
        ...

    @api.model
    def generate_xlsx_report(self, workbook, allowed_company):
        ...

    @api.model
    def get_xlsx(self, allowed_company):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        self.generate_xlsx_report(workbook, allowed_company)
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        return generated_file

    @api.model
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
            'bg_color': '#dbeef4',
            'text_wrap': True,
        }
        subtotal_format = {
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#c2f7ad'
        }
        normal_format = {
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        }
        datetime_format = {
            'num_format': "dd/mm/yy hh:mm:ss",
        }
        align_right = {'align': 'right'}
        datetime_format.update(normal_format)
        float_number_format = {}
        center_format = copy.copy(normal_format)
        right_format = copy.copy(normal_format)
        italic_format = copy.copy(normal_format)
        italic_format.update({
            'border': 0,
            'italic': 1,
        })
        int_number_format = {}

        center_format.update({'align': 'center'})
        right_format.update({'align': 'right'})
        float_number_format.update(normal_format)
        int_number_format.update(normal_format)
        int_number_format.update(align_right)
        float_number_title_format = float_number_format.copy()
        float_number_title_format.update(title_format)
        int_number_title_format = int_number_format.copy()
        int_number_title_format.update(title_format)

        title_format = workbook.add_format(title_format)
        datetime_format = workbook.add_format(datetime_format)
        normal_format = workbook.add_format(normal_format)
        italic_format = workbook.add_format(italic_format)
        center_format = workbook.add_format(center_format)
        right_format = workbook.add_format(right_format)
        header_format = workbook.add_format(header_format)

        float_number_format.update(align_right)
        float_number_format = workbook.add_format(float_number_format)
        float_number_format.set_num_format('#,##0.00')
        percentage_format = int_number_format.copy()
        int_number_format = workbook.add_format(int_number_format)
        int_number_format.set_num_format('#,##0')
        int_subtotal_format = workbook.add_format(subtotal_format)
        int_subtotal_format.set_num_format('#,##0')
        int_subtotal_format.set_align('right')
        subtotal_format = workbook.add_format(subtotal_format)
        percentage_format.update({'align': 'right', 'num_format': '0%'})
        percentage_format = workbook.add_format(percentage_format)

        float_number_title_format = workbook.add_format(float_number_title_format)
        float_number_title_format.set_num_format('#,##0.00')
        int_number_title_format = workbook.add_format(int_number_title_format)
        int_number_title_format.set_num_format('#,##0')

        return {
            'header_format': header_format,
            'title_format': title_format,
            'datetime_format': datetime_format,
            'normal_format': normal_format,
            'italic_format': italic_format,
            'center_format': center_format,
            'right_format': right_format,
            'float_number_format': float_number_format,
            'int_number_format': int_number_format,
            'float_number_title_format': float_number_title_format,
            'int_number_title_format': int_number_title_format,
            'subtotal_format': subtotal_format,
            'int_subtotal_format': int_subtotal_format,
            'percentage_format': percentage_format,
        }
