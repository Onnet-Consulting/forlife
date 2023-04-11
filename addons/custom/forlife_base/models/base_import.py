# -*- coding: utf-8 -*-

import datetime

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.tools import config, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None


class Import(models.TransientModel):
    _inherit = 'base_import.import'

    def execute_import(self, fields, columns, options, dryrun=False):
        if dryrun:
            return super(Import, self.with_context(test_import=True)).execute_import(fields, columns, options, dryrun=dryrun)
        return super(Import, self).execute_import(fields, columns, options, dryrun=dryrun)

    def _read_xls_book(self, book, sheet_name):
        sheet = book.sheet_by_name(sheet_name)
        rows = []
        col_attribute = 0
        col_value = 0
        dic_col = {}
        # emulate Sheet.get_rows for pre-0.9.4
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            for colx, cell in enumerate(row, 1):
                if self.res_model == 'product.template':
                    attribute_id = self.env['product.attribute'].search([('name', '=', str(cell.value))])
                    if attribute_id and col_attribute == 0:
                        values.append('Thuộc tính sản phẩm / Thuộc tính')
                        col_attribute = colx
                        dic_col[colx] = cell.value
                        continue
                    elif attribute_id and col_value == 0:
                        values.append('Thuộc tính sản phẩm / Giá trị')
                        col_value = colx
                        dic_col[colx] = cell.value
                        break
                    if str(cell.value).find(','):
                        arr_value = str(cell.value).split(',')
                    else:
                        arr_value = [str(cell.value)]
                    check = False
                    for value in arr_value:
                        val_attribute_id = self.env['product.attribute.value'].search(
                            [('name', '=', str(value).replace(' ', ''))])
                        if val_attribute_id:
                            check = True
                            if len(values) == col_attribute - 1:
                                values += [dic_col[colx], str(value).replace(' ', '')]
                                rows.append(values)
                                values = []
                                continue
                            for i in range(1, col_attribute):
                                values.append('')
                            values += [dic_col[colx], str(value).replace(' ', '')]
                            rows.append(values)
                            values = []
                            continue
                    if check:
                        continue
                    if colx == col_value:
                        break
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        str(cell.value)
                        if is_float
                        else str(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # emulate xldate_as_datetime for pre-0.9.3
                    dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if is_datetime
                        else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u'True' if cell.value else u'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s") % {
                            'row': rowx,
                            'col': colx,
                            'cell_value': xlrd.error_text_from_code.get(cell.value,
                                                                        _("unknown error code %s", cell.value))
                        }
                    )
                else:
                    values.append(cell.value)
            if any(x for x in values if x.strip()):
                rows.append(values)

        # return the file length as first value
        return sheet.nrows, rows