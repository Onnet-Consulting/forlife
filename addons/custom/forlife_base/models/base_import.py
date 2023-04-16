
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def _read_xls_book(self, book, sheet_name):
        if self.res_model == 'product.template':
            return self._read_xls_book_product(book, sheet_name)

        return super(Import, self)._read_xls_book(book, sheet_name)

    def _read_xls_book_product(self, book, sheet_name):
        sheet = book.sheet_by_name(sheet_name)
        rows = []
        dic_col = {}
        attributes = {}
        for rowx, row in enumerate(map(sheet.row, range(1)), 1):
            for colx, cell in enumerate(row, 1):
                attribute_id = self.env['product.attribute'].search([('name', '=', str(cell.value))])
                if attribute_id:
                    dic_col[colx] = str(cell.value)
                    attributes[colx] = attribute_id
        col_number = 0
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            row_attrs = []
            if rowx == 1 and dic_col:
                for colx, cell in enumerate(row, 1):
                    if not dic_col.get(colx, False):
                        values.append(str(cell.value))
                values.append("Thuộc tính sản phẩm / Thuộc tính")
                values.append("Thuộc tính sản phẩm / Giá trị / ID Cơ sở dữ liệu")
                col_number = len(values) - 1
            else:
                for colx, cell in enumerate(row, 1):
                    cell_value = str(cell.value)
                    if dic_col and dic_col.get(colx, False):
                        if cell.value and cell_value.strip():
                            cell_values = cell_value.split(',')
                            value_attrs = []
                            attr_val_ids = []
                            for attr_val in cell_values:
                                attr = attributes[colx]
                                list_attr_vals = attr.value_ids
                                val_attribute_id = 0
                                for val in list_attr_vals:
                                    if val.code == attr_val.strip():
                                        val_attribute_id = val.id
                                    # raise ValueError(_("Không tồn tại giá trị {} của thuộc tính {}".format(cell_value, dic_col[colx])))
                                attr_val_ids.append(str(val_attribute_id))
                            for i in range(1, col_number):
                                value_attrs.append('')
                            value_attrs.append(str(dic_col[colx]))
                            value_attrs.append(','.join(attr_val_ids))
                            row_attrs.append(value_attrs)
                    else:
                        if cell.ctype is xlrd.XL_CELL_NUMBER:
                            is_float = cell.value % 1 != 0.0
                            values.append(
                                str(cell.value)
                                if is_float
                                else str(int(cell.value))
                            )
                        elif cell.ctype is xlrd.XL_CELL_DATE:
                            is_datetime = cell.value % 1 != 0.0
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
            if row_attrs:
                values.append(row_attrs[0][-2])
                values.append(row_attrs[0][-1])
                row_attrs.pop(0)
            rows.append(values)
            rows += row_attrs
        return len(rows), rows
