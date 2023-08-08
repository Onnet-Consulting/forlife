
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

    # FIXME: if other module override this method, re-check the context
    def execute_import(self, fields, columns, options, dryrun=False):
        if dryrun:
            return super(Import, self.with_context(test_import=True)).execute_import(fields, columns, options, dryrun=dryrun)
        return super(Import, self).execute_import(fields, columns, options, dryrun=dryrun)

    def _read_xls_book(self, book, sheet_name):
        if self.res_model == 'product.template':
            return self._read_xls_book_product(book, sheet_name)

        return super(Import, self)._read_xls_book(book, sheet_name)

    def _get_barcode_from_db(self, list_barcode=[]):
        query = 'SELECT barcode FROM product_template WHERE barcode in %(list_barcode)s'
        self.env.cr.execute(query, {'list_barcode': tuple(list_barcode)})
        data = self.env.cr.fetchall()
        return [barcode[0] for barcode in data]

    def _read_xls_book_product(self, book, sheet_name):
        sheet = book.sheet_by_name(sheet_name)
        rows = []
        dic_col = {}
        attributes = {}
        col_barcode = -1
        list_barcodes = []
        barcode_exits = []

        for rowx, row in enumerate(map(sheet.row, range(1)), 1):
            for colx, cell in enumerate(row, 1):
                if rowx == 1:
                    # if 'Barcode' == str(cell.value):
                    #     col_barcode = colx
                    attribute_id = self.env['product.attribute'].search([('name', '=', str(cell.value))])
                    if attribute_id:
                        dic_col[colx] = str(cell.value)
                        attributes[colx] = attribute_id
                # elif col_barcode > -1:
                #     if colx == col_barcode:
                #         list_barcodes.append(str(cell.value))

        # if list_barcodes:
        #     barcode_exits = self._get_barcode_from_db(list_barcodes)

        col_number = 0
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            row_attrs = []
            add_row = True
            if rowx == 1 and dic_col:
                for colx, cell in enumerate(row, 1):
                    if not dic_col.get(colx, False):
                        values.append(str(cell.value))
                values.append("Thuộc tính sản phẩm / Thuộc tính / ID Cơ sở dữ liệu")
                values.append("Thuộc tính sản phẩm / Giá trị / ID Cơ sở dữ liệu")
                col_number = len(values) - 1
            else:
                for colx, cell in enumerate(row, 1):
                    cell_value = cell.value
                    # if colx == col_barcode:
                    #     if str(cell_value) in barcode_exits:
                    #         add_row = False
                    #         break
                    if dic_col and dic_col.get(colx, False):
                        if type(cell_value) == float:
                            cell_value = int(cell_value)
                        cell_value = str(cell_value)
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
                            value_attrs.append(str(attr.id))
                            value_attrs.append(','.join(attr_val_ids))
                            row_attrs.append(value_attrs)
                    else:
                        if isinstance(cell.value, str):
                            cell.value.replace(' 00:00:00', '')
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
                                                                                _("unknown error code %s",
                                                                                  cell.value))
                                }
                            )
                        else:
                            values.append(cell.value)
                if row_attrs:
                    values.append(row_attrs[0][-2])
                    values.append(row_attrs[0][-1])
                    row_attrs.pop(0)
                else:
                    values.append('')
                    values.append('')
            if add_row:
                rows.append(values)
            rows += row_attrs

        return len(rows), rows
