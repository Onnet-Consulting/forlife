# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero
from odoo import api, fields, models, _, tools
import xlrd
import base64

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    file_binary = fields.Binary('File Binary')
    file_binary_name = fields.Char('File Binary Name')

    def check_format_file_excel(self, file_name):
        if file_name is False:
            raise ValidationError(_('Thay đổi loại tệp thành .xlsx hoặc xls.'))
        if file_name.endswith('.xls') == False and file_name.endswith('.xlsx') == False:
            self.file_binary = None
            self.file_binary_name = None
            raise ValidationError(_('Thay đổi loại tệp thành .xlsx hoặc xls.'))

    def is_number(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def import_file_1st(self):
        if not self.line_ids:
            return
        # try:
        """ Validate file null """
        if self.file_binary is None:
            raise ValidationError(_('Không tìm thấy file import. Vui lòng chọn lại file import.'))
        """ Validate format file """
        self.check_format_file_excel(self.file_binary_name)
        file_import = self.file_binary
        data = base64.decodebytes(file_import)
        excel = xlrd.open_workbook(file_contents=data)
        sheet = excel.sheet_by_index(0)
        Product = self.env['product.product']
        StockInventoryLine = self.env['stock.inventory.line']

        lst_line = []

        index = 1
        while index < sheet.nrows:
            barcode = (sheet.cell(index, 3).value).strip()
            product_id = Product.search([('barcode', '=', barcode)], limit=1)
            if not product_id:
                continue
            qty = sheet.cell(index, 5).value
            if not self.is_number(qty):
                raise ValidationError(_("Số lượng xác nhận lần 1 không hợp lệ tại dòng '%s'." % (index + 1)))
            invetory_line_id = StockInventoryLine.search([('barcode', '=', barcode), ('inventory_id', '=', self.id)], limit=1)
            if invetory_line_id:
                invetory_line_id.write({
                    'x_first_qty': qty,
                    'product_qty': qty
                })
            else:
                invetory_line_id = StockInventoryLine.create({
                    'inventory_id': self.id,
                    'product_id': product_id.id,
                    'location_id': self.location_id.id,
                    'product_uom_id': product_id.uom_id.id,
                    'x_first_qty': qty,
                    'product_qty': qty
                })
            lst_line.append(invetory_line_id.id)
            index += 1

        line_not_exists_excel_ids = self.line_ids.filtered(lambda x: x.id not in lst_line)
        if line_not_exists_excel_ids:
            for line_not_exists_excel_id in line_not_exists_excel_ids:
                line_not_exists_excel_id.write({
                    'x_first_qty': 0,
                    'product_qty': 0
                })

        self.file_binary = False
        self.file_binary_name = False

    def import_file_2nd(self):
        if not self.line_ids:
            return
        # try:
        """ Validate file null """
        if self.file_binary is None:
            raise ValidationError(_('Không tìm thấy file import. Vui lòng chọn lại file import.'))
        """ Validate format file """
        self.check_format_file_excel(self.file_binary_name)
        file_import = self.file_binary
        data = base64.decodebytes(file_import)
        excel = xlrd.open_workbook(file_contents=data)
        sheet = excel.sheet_by_index(0)
        Product = self.env['product.product']
        StockInventoryLine = self.env['stock.inventory.line']

        lst_line = []

        index = 1
        while index < sheet.nrows:
            barcode = (sheet.cell(index, 3).value).strip()
            product_id = Product.search([('barcode', '=', barcode)], limit=1)
            if not product_id:
                continue
            qty = sheet.cell(index, 6).value
            if not self.is_number(qty):
                raise ValidationError(_("Số lượng xác nhận lần 2 không hợp lệ tại dòng '%s'." % (index + 1)))
            invetory_line_id = StockInventoryLine.search([('barcode', '=', barcode), ('inventory_id', '=', self.id)], limit=1)
            if invetory_line_id:
                invetory_line_id.write({
                    'product_qty': qty
                })
            else:
                invetory_line_id = StockInventoryLine.create({
                    'inventory_id': self.id,
                    'product_id': product_id.id,
                    'location_id': self.location_id.id,
                    'product_uom_id': product_id.uom_id.id,
                    'x_first_qty': 0,
                    'product_qty': qty

                })
            lst_line.append(invetory_line_id.id)
            index += 1

        line_not_exists_excel_ids = self.line_ids.filtered(lambda x: x.id not in lst_line)
        if line_not_exists_excel_ids:
            for line_not_exists_excel_id in line_not_exists_excel_ids:
                line_not_exists_excel_id.write({
                    'product_qty': 0
                })

        self.file_binary = False
        self.file_binary_name = False