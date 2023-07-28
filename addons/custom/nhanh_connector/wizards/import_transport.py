import base64
import xlrd
from odoo import fields, api, models, _
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo.modules.module import get_resource_path


class ImportProductionFromExcel(models.TransientModel):
    _name = 'import.transport.from.excel'
    _description = "Transport import"

    name = fields.Char(default='Nhập từ excel')
    file = fields.Binary(string='File excel')
    file_name = fields.Char(string='Tên file')
    file_template = fields.Binary(string='Template default', compute='get_default_template')

    def get_default_template(self):
        for rec in self:
            path = get_resource_path('nhanh_connector', 'data/xml', 'template_import_transport.xlsx')
            rec.file_template = base64.b64encode(open(path, "rb").read())

    def download_template(self):
        export = {
            'type': 'ir.actions.act_url',
            'name': 'Export fee',
            'url': '/web/content/%s/%s/file_template/template_van_don.xlsx?download=true' % (self._name, self.id),
        }
        return export

    def prepare_values(self, orders, location_ids, type):
        create_values = []
        for location in location_ids:
            order = orders.filtered(lambda x: not x.x_is_change and x.x_location_id == location)
            value = {
                'stock_id': location.location_id.id,
                'location_id': location.id,
                'date': datetime.now(),
                'type': type,
                'company_id': self.env.company.id,
                'session_line': [(0, 0, {
                    'order_id': o.id,
                    'nhanh_id': o.nhanh_id,
                }) for o in order]
            }
            create_values.append(value)
        return create_values

    def apply(self):
        wb = xlrd.open_workbook(file_contents=base64.decodebytes(self.file))
        order_code = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=0))[1:]

        list_code = []
        for code in order_code:
            list_code.append(code[0])

        orders = self.env['sale.order'].search([('nhanh_id', 'in', list_code), ('state', 'in', ['sale'])])
        list_code_exist = orders.mapped('nhanh_id')
        different_elements = set(list_code).symmetric_difference(set(list_code_exist))
        code_not_exists = list(different_elements)
        if code_not_exists:
            raise ValidationError(_('Tồn tại code không có đơn hàng là %s' % code_not_exists))

        location_out_ids = orders.filtered(lambda x: not x.x_is_return).mapped('x_location_id')
        location_in_ids = orders.filtered(lambda x: x.x_is_return).mapped('x_location_id')
        create_values = self.prepare_values(orders=orders, location_ids=location_in_ids, type='in')
        create_values += self.prepare_values(orders=orders, location_ids=location_out_ids, type='out')
        session = self.env['transportation.session'].create(create_values)
        action = self.env.ref('nhanh_connector.transportation_management_action').read()[0]
        action['target'] = 'main'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đã tạo thành công %s bản ghi' % len(session),
                'type': 'success',
                'sticky': False,
                'next': action,
            }
        }

