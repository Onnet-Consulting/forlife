import base64
import urllib
from odoo.addons.nhanh_connector.models import constant
from odoo import _, models, fields, api
from odoo.exceptions import ValidationError
import datetime, logging
import requests
import json

_logger = logging.getLogger(__name__)


class ProductNhanh(models.Model):
    _inherit = 'product.template'

    nhanh_id = fields.Integer(string="Id Nhanh.Vn")
    code_product = fields.Char(string="Mã sản phẩm")
    ## Nếu tạo sản phẩm từ Odoo == True else == False
    check_data_odoo = fields.Boolean(string='Check dữ liệu từ odoo or Nhanh', default=True)
    width_product = fields.Float('Width')
    height_product = fields.Float('Height')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        self.synchronized_create_product(res)
        return res

    def synchronized_create_product(self, res):
        if res.check_data_odoo == True:
            nhanh_configs = constant.get_nhanh_configs(self)
            if 'nhanh_connector.nhanh_app_id' in nhanh_configs or 'nhanh_connector.nhanh_business_id' in nhanh_configs \
                    or 'nhanh_connector.nhanh_access_token' in nhanh_configs:
                data = [{
                    "id": res.id,
                    "name": res.name,
                    "code": res.code_product,
                    "barcode": res.barcode if res.barcode else '',
                    "price": int(res.list_price),
                    "shippingWeight": int(res.weight),
                    "status": 'New'
                }]

                try:
                    res_server = self.post_data_nhanh(data)
                    status_nhanh = 1
                    res_json = res_server.json()
                    if status_nhanh == 1:
                        if res_json['code'] == 0:
                            _logger.info(f'Get order error {res["messages"]}')
                            return False
                        else:
                            value = []
                            for item in res_json['data']['ids']:
                                value.append(res_json['data']['ids'].get(item))
                            res.write(
                                {
                                    'nhanh_id': int(value[0])
                                }
                            )
                except Exception as ex:
                    _logger.info(f'Get orders from NhanhVn error {ex}')
        return True

    def write(self, vals):
        res = super().write(vals)
        for item in self:
            data = '[{"id": "' + str(item.id) + '","idNhanh":"' + str(item.nhanh_id) + '", "price": "' + str(int(
                item.list_price)) + '", "name": "' + str(item.name) + '", "shippingWeight": "' + str(
                int(item.weight)) + '", "status": "' + 'Active' + '", "barcode": "' + str(
                    item.barcode if item.barcode else '') + '"}]'
            self.synchronized_price_nhanh(data)
        return res

    def unlink(self):
        for item in self:
            data = '[{"id": "' + str(item.id) + '","idNhanh":"' + str(item.nhanh_id) + '", "price": "' + str(int(
                item.list_price)) + '", "name": "' + str(item.name) + '", "shippingWeight": "' + str(
                int(item.weight)) + '", "status": "' + 'Inactive' + '", "barcode": "' + str(
                item.barcode if item.barcode else '') + '"}]'
            self.synchronized_price_nhanh(data)
        res = super().unlink()

        return res

    def synchronized_price_nhanh(self, data):
        nhanh_configs = constant.get_nhanh_configs(self)
        if 'nhanh_connector.nhanh_app_id' in nhanh_configs or 'nhanh_connector.nhanh_business_id' in nhanh_configs \
                or 'nhanh_connector.nhanh_access_token' in nhanh_configs:
            status_nhanh = 1
            try:
                res_server = self.post_data_nhanh(data)
                res_json = res_server.json()
            except Exception as ex:
                status_nhanh = 0
                _logger.info(f'Get orders from NhanhVn error {ex}')
            if status_nhanh == 1:
                if res_json['code'] == 0:
                    _logger.info(f'Get order error {res_json["messages"]}')
                    return False
                else:
                    pass
        return True

    def post_data_nhanh(self, data):
        url = f"{constant.base_url()}/product/add"
        payload = {
            'version': constant.get_params(self)['version'],
            'appId': constant.get_params(self)['appId'],
            'businessId': constant.get_params(self)['businessId'],
            'accessToken': constant.get_params(self)['accessToken'],
            'data': json.dumps(data)
        }
        res_server = requests.post(url, data=payload)
        return res_server

