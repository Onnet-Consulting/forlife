# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
import xlrd


class ImportStoreFirstOrder(models.TransientModel):
    _name = 'import.store.first.order'
    _description = 'Import store first order'

    brand_id = fields.Many2one("res.brand", string="Brand")
    row_start = fields.Integer('Row start', default=2)
    import_file = fields.Binary(attachment=False, string='Upload file')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='Error file')
    error_file_name = fields.Char(default='Error.txt')

    def download_template_file(self):
        attachment_id = self.env.ref(f'forlife_point_of_sale.template_import_store_first_order')
        return {
            'type': 'ir.actions.act_url',
            'name': 'Get template',
            'url': f'web/content/?model=ir.attachment&id={attachment_id.id}&filename_field=name&field=datas&download=true&name={attachment_id.name}',
            'target': 'new'
        }

    @api.onchange('import_file')
    def onchange_import_file(self):
        self.error_file = False

    def action_import(self):
        self.ensure_one()
        if not self.import_file or not self.brand_id:
            raise ValidationError(_("Please choose brand and upload file template before click Import button !"))
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        self._cr.execute(f"""
select (select json_object_agg(code, id) from store where brand_id = {self.brand_id.id})                   as stores,
       (select json_object_agg(rp.phone, rp.id) from res_partner rp
            join res_partner_group rpg on rp.group_id = rpg.id and rpg.code = 'C')                         as customers,
       (select json_object_agg(customer_id, 1) from store_first_order where brand_id = {self.brand_id.id}) as data_exist
""")
        data = self._cr.dictfetchone()

        customer_by_phone = data.get('customers') or {}
        data_exist = data.get('data_exist') or {}
        stores = data.get('stores') or {}
        values = []
        error = []
        duplicate_phone = {}
        for index, line in enumerate(list(self.env['res.utility'].read_xls_book(workbook, 0))[max(0, self.row_start - 1):]):
            customer_phone = line[0] or ''
            store_code = line[1] or ''
            customer_id = customer_by_phone.get(customer_phone)
            store_id = stores.get(store_code)
            if not customer_id:
                error.append(f"Dòng {index + self.row_start}, không tìm thấy khách hàng có số điện thoại là '{customer_phone}'")
            if not store_id:
                error.append(f"Dòng {index + self.row_start}, không tìm thấy cửa hàng có mã là '{store_code}' thuộc thương hiệu '{self.brand_id.name}'")
            if customer_id and data_exist.get(str(customer_id)):
                error.append(f"Dòng {index + self.row_start}, khách hàng có số điện thoại '{customer_phone}' đã được ghi nhận phát sinh đơn đầu tiên tại 1 cửa hàng")
            if duplicate_phone.get(customer_phone):
                error.append(f"Dòng {index + self.row_start}, số điện thoại '{customer_phone}' bị trùng lặp")
            duplicate_phone.update({customer_phone: 1})
            if not error:
                val = {
                    'customer_id': customer_id,
                    'brand_id': self.brand_id.id,
                    'store_id': store_id,
                }
                values.append(val)
        if error:
            return self.return_error_log('\n'.join(error))
        if values:
            x = self.env['store.first.order'].sudo().with_delay(description='Import store first order').create(values)
            action = self.env.ref('queue_job.action_queue_job').read()[0]
            action['domain'] = [('uuid', '=', x.uuid)]
            action['context'] = '{}'
            return action
        return True

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env.ref('forlife_point_of_sale.import_store_first_order_action').read()[0]
        action['res_id'] = self.id
        return action
