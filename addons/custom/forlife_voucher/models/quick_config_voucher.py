from io import BytesIO
from odoo import fields, api, models
import xlrd
import xlsxwriter
import base64
import tempfile


class QuickConfigVoucher(models.Model):
    _name = 'quick.config.voucher'
    _description = "Quick Config Voucher"

    name = fields.Char(string='Name', default='Đổi trạng thái voucher', readonly=True)
    method = fields.Selection([('active', 'Hiệu lực'), ('in_active', 'Vô hiệu')],
                              string='Phương thức đổi', required=True)
    voucher_ids = fields.Many2many('voucher.voucher', string='Voucher')
    file_import = fields.Binary(string='File Excel')
    file_name = fields.Char(string='File name')
    template_excel = fields.Binary(string='Template', compute='_get_template')
    show_message = fields.Boolean(default=False)
    message_invalid = fields.Text(string='Lỗi')

    def _get_template(self):
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        # Lấy đường dẫn của file tạm
        temp_file_path = temp_file.name
        workbook = xlsxwriter.Workbook(temp_file_path)
        worksheet = workbook.add_worksheet(u'Sheet0')

        header = ['Code']
        lines = [header] + [['AXBIDSL12']]

        header_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'font_size': '11',
            'text_wrap': True,
            'italic': False,
            'border': 1,
        })
        row = 0
        for line in lines:
            col = 0
            for item in line:
                if row == 0:
                    worksheet.write(row, col, item, header_format)
                else:
                    worksheet.write(row, col, item)
                col += 1
            row += 1
        worksheet.set_column(0, len(header), 20)
        worksheet.set_row(0, 30)
        workbook.close()
        # Đóng file
        temp_file.close()
        self.template_excel = base64.b64encode(open(temp_file_path, "rb").read())

    @api.onchange('template_excel')
    def _onchange_template_excel(self):
        self.show_message = False

    @api.onchange('method')
    def _onchange_method(self):
        self.show_message = False
        self.voucher_ids = [(5, 0, 0)]

    def import_xlsx(self):
        wb = xlrd.open_workbook(file_contents=base64.decodebytes(self.file_import))
        data = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=0))[1:]
        list_code = []
        for d in data:
            list_code += d
        vouchers = self.env['voucher.voucher'].search([('name', 'in', list_code), ('using_limit', '=', 1)])
        message_invalid = ''
        if self.method == 'active':
            valid_vouchers = vouchers.filtered(lambda x: x.state == 'off value')
            invalid_vouchers = vouchers.filtered(lambda x: x.state == 'sold')

        else:
            valid_vouchers = vouchers.filtered(lambda x: x.state == 'sold')
            invalid_vouchers = vouchers.filtered(lambda x: x.state == 'off value')

        list_code_invalid = invalid_vouchers.mapped('name') + list(set(valid_vouchers.mapped('name')) ^ set(list_code))
        show_message = False
        if list_code_invalid:
            show_message = True
            message_invalid = 'Các code không hợp lệ trong file excel %s' % list(set(list_code_invalid))

        self.write({
            'voucher_ids': [(6, 0, valid_vouchers.ids)],
            'message_invalid': message_invalid,
            'show_message': show_message
        })

    def download_temp(self):
        export = {
            'type': 'ir.actions.act_url',
            'name': 'Export fee',
            'url': '/web/content/%s/%s/template_excel/template.xlsx?download=true' % (self._name, self.id),
        }
        self.template_excel = False
        return export

    def action_confirm(self):
        if self.method == 'active':
            for v in self.voucher_ids:
                v.write({'state': 'sold'})
        else:
            for v in self.voucher_ids:
                v.write({'state': 'off value'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': 'Thay đổi trạng thái voucher thành công!.',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
