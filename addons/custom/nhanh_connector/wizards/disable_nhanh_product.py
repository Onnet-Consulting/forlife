import base64
import xlrd
import json
import requests
import time

from odoo import _, api, fields, models
from odoo.addons.nhanh_connector.models import constant
from odoo.exceptions import ValidationError


class DisableNhanhProduct(models.TransientModel):
    _name = 'disable.nhanh.product'

    import_file = fields.Binary(attachment=False, string='Upload file')
    import_file_name = fields.Char()
    brand_id = fields.Many2one('res.brand', string="Brand", required=1)

    def action_import(self):
        if not self.import_file:
            raise ValidationError("Vui lòng update file import")
        excel = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        sheet = excel.sheet_by_index(0)
        batch = sheet.nrows // 100 + 1
        for item in range(0, batch):
            data = []
            for row in range(item * 100 + 1, min(item * 100 + 101, sheet.nrows)):
                if not sheet.cell(row, 0).value.strip():
                    continue
                try:
                    nhanh_id = int(sheet.cell(row, 0).value.strip())
                    nhanh_product_name = sheet.cell(row, 1).value.strip()
                    price = int(sheet.cell(row, 2).value) if sheet.cell(row, 2).value else 0
                    # product_id = self.env['product.product'].sudo().search([('nhanh_id','=', nhanh_id)])
                    # if not product_id:
                    #     continue
                    data.append({
                        "idNhanh": nhanh_id,
                        "name": nhanh_product_name,
                        "id": 100,
                        "price": price,
                        "status": 'Inactive'
                    })
                except:
                    continue

            nhanh_configs = constant.get_nhanh_configs(self, brand_ids=[self.brand_id.id]).get(self.brand_id.id)
            if nhanh_configs.get('nhanh_connector.nhanh_app_id', '') or nhanh_configs.get(
                    'nhanh_connector.nhanh_business_id', '') or nhanh_configs.get('nhanh_connector.nhanh_access_token',
                                                                                  ''):
                url = f"{constant.base_url()}/product/add"
                payload = {
                    'version': '2.0',
                    'appId': nhanh_configs.get('nhanh_connector.nhanh_app_id', ''),
                    'businessId': nhanh_configs.get('nhanh_connector.nhanh_business_id', ''),
                    'accessToken': nhanh_configs.get('nhanh_connector.nhanh_access_token', ''),
                    'data': json.dumps(data)
                }
                res_server = requests.post(url, data=payload)
                result = res_server.json()
                if result.get('code') == 0:
                    raise ValidationError(result.get('messages'))
                time.sleep(5)
