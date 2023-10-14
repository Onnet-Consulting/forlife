# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import xlrd
import base64


class ImportVendorBack(models.TransientModel):
    _name = 'import.vendor.back'
    _inherit = 'report.base'
    _description = 'Nhập kê khai hóa đơn GTGT'

    import_file = fields.Binary(attachment=False, string='File nhập')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='File lỗi')
    error_file_name = fields.Char(default='Tệp lỗi.txt')

    @api.onchange('import_file')
    def onchange_import_file(self):
        self.error_file = False

    @api.model
    def generate_xlsx_report(self, workbook, allowed_company, **kwargs):
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Kê khai hóa đơn GTGT')
        sheet.freeze_panes(1, 0)
        sheet.set_row(0, 30)
        sheet.write(0, 0, 'Tên nhà cung cấp', formats.get('title_format'))
        sheet.write(0, 1, 'Mã số thuế', formats.get('title_format'))
        sheet.write(0, 2, 'Địa chỉ', formats.get('title_format'))
        sheet.write(0, 3, 'Số hóa đơn', formats.get('title_format'))
        sheet.write(0, 4, 'Diễn giải hóa đơn', formats.get('title_format'))
        sheet.write(0, 5, 'Thành tiền', formats.get('title_format'))
        sheet.write(0, 6, 'Ngày hóa đơn(DD/MM/YYYY)', formats.get('title_format'))
        sheet.write(0, 7, 'Thuế (tham khảo sheet Thuế có sẵn)', formats.get('title_format'))
        sheet.write(0, 8, 'Hạn xử lý (DD/MM/YYYY)', formats.get('title_format'))
        sheet.set_column(0, 8, 20)

        sheet_tax = workbook.add_worksheet('Thuế có sẵn')
        sheet_tax.freeze_panes(1, 0)
        sheet_tax.set_row(0, 30)
        sheet_tax.write(0, 0, 'Tên thuế', formats.get('title_format'))
        sheet_tax.write(0, 1, '% thuế', formats.get('title_format'))
        sheet_tax.set_column(0, 2, 30)
        row = 1
        for tax in self.env['account.tax'].with_company(self.env.company).search([]):
            sheet_tax.write(row, 0, tax.name, formats.get('normal_format'))
            sheet_tax.write(row, 1, tax.amount / 100, formats.get('percentage_format'))
            row += 1
        
    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError("Vui lòng tải lên file mẫu trước khi nhấn nút Nhập !")
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        data = list(self.env['res.utility'].read_xls_book(workbook, 0))[1:]
        error = []
        values = []
        if data:
            company_id = self.env.company.id
            self._cr.execute(f"""
                select json_object_agg(name, id) as value
                from (select coalesce(name::json ->> 'vi_VN', name::json ->> 'en_US') as name, id
                      from account_tax
                      where company_id = {company_id}) as x""")
            result = (self._cr.dictfetchone() or {}).get('value') or {}
            invoice_id = self._context.get('invoice_id')
            for idx, line in enumerate(data, start=2):
                tax_id = result.get(line[7].strip())
                if not tax_id and line[7]:
                    error.append(f"Dòng {idx}, Thuế '{line[7]}' không tồn tại trong hệ thống")
                if not error:
                    values.append({
                        'vendor_back_id': invoice_id,
                        'vendor': line[0],
                        'code_tax': line[1],
                        'street_ven': line[2],
                        'company_id': company_id,
                        'invoice_reference': line[3],
                        'description': line[4],
                        'price_subtotal_back': line[5],
                        '_x_invoice_date': line[6] or False,
                        'tax_percent': tax_id or False,
                        'date_due': line[8] or False,
                    })

        if error:
            return self.return_error_log('\n'.join(error))
        if values:
            self.env['vendor.back'].create(values)
        return True

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_invoice.action_import_vendor_back')
        action['res_id'] = self.id
        return action
