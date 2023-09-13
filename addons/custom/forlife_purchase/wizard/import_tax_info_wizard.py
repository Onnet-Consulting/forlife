# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import xlrd
import base64
import copy


class ImportTaxInfoWizard(models.TransientModel):
    _name = 'import.tax.info.wizard'
    _inherit = 'report.base'
    _description = 'Nhập thông tin thuế'

    import_file = fields.Binary(attachment=False, string='Tải lên tệp')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='Tệp lỗi')
    error_file_name = fields.Char(default='Tệp lỗi.txt')
    po_id = fields.Many2one('purchase.order', 'PO')

    @api.model
    def generate_xlsx_report(self, workbook, allowed_company, **kwargs):
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Mẫu nhập thông tin thuế')
        sheet.freeze_panes(1, 0)
        sheet.set_row(0, 30)
        TITLES = [
            'Database ID', 'Sản phẩm', 'Mô tả', 'Thành tiền VND', 'Số lượng', '% Thuế nhập khẩu', 'Thuế nhập khẩu',
            '% Thuế tiêu thụ đặc biệt', 'Thuế tiêu thụ đặc biệt', '% Thuế GTGT', 'Thuế GTGT', 'Tổng tiền thuế'
        ]
        for idx, title in enumerate(TITLES):
            sheet.write(0, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES) - 1, 20)
        row = 1
        for line in self.po_id.exchange_rate_line_ids:
            sheet.write(row, 0, line.id, formats.get('center_format'))
            sheet.write(row, 1, line.product_id.name or '', formats.get('normal_format'))
            sheet.write(row, 2, line.description or '', formats.get('normal_format'))
            sheet.write(row, 3, line.total_vnd_exchange or 0, formats.get('int_number_format'))
            sheet.write(row, 4, line.product_qty or 0, formats.get('int_number_format'))
            sheet.write(row, 5, line.import_tax or 0, formats.get('float_number_format'))
            sheet.write(row, 6, line.tax_amount or 0, formats.get('int_number_format'))
            sheet.write(row, 7, line.special_consumption_tax or 0, formats.get('float_number_format'))
            sheet.write(row, 8, line.special_consumption_tax_amount or 0, formats.get('int_number_format'))
            sheet.write(row, 9, line.vat_tax or 0, formats.get('float_number_format'))
            sheet.write(row, 10, line.vat_tax_amount or 0, formats.get('int_number_format'))
            sheet.write(row, 11, line.total_tax_amount or 0, formats.get('int_number_format'))
            row += 1

    def get_filename(self):
        return f"Đơn mua hàng nhập khẩu {self.po_id.name or ''}"

    @api.onchange('import_file')
    def onchange_import_file(self):
        self.error_file = False

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError("Vui lòng tải lên file mẫu trước khi nhấn nút nhập !")
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        data_import = list(self.env['res.utility'].read_xls_book(workbook, 0))[1:]
        if not data_import:
            return False
        error = []
        data_write = []
        self._cr.execute(f"""select json_object_agg(id, array[
                                    coalesce(import_tax, 0),
                                    coalesce(special_consumption_tax, 0),
                                    coalesce(vat_tax, 0)]) as data
                                from purchase_order_line
                                where order_id = {self.po_id.id}""")
        old_tax_data = self._cr.fetchone()[0] or {}
        for index, data in enumerate(data_import, start=2):
            if not data[0] or not old_tax_data.get(data[0]):
                error.append(f"Dòng {index}: ID '{data[0]}' không khớp với dữ liệu trong tab Thông tin thuế")
            elif not error:
                old_tax_detail = old_tax_data.get(data[0])
                import_tax = float(data[5])
                special_consumption_tax = float(data[7])
                vat_tax = float(data[9])
                if old_tax_detail[0] != import_tax or old_tax_detail[1] != special_consumption_tax or old_tax_detail[2] != vat_tax:
                    data_write.append((1, int(data[0]), {
                        'import_tax': import_tax,
                        'special_consumption_tax': special_consumption_tax,
                        'vat_tax': vat_tax,
                    }))
        if error:
            return self.return_error_log('\n'.join(error))
        elif data_write:
            self.po_id.write({'exchange_rate_line_ids': data_write})
        return True

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env.ref('forlife_purchase.import_tax_info_wizard_action').read()[0]
        action['res_id'] = self.id
        return action
