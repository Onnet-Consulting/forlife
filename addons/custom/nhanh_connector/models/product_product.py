# -*- coding: utf-8 -*-

from odoo.addons.nhanh_connector.models import constant
from odoo import _, models, fields, api
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    nhanh_id = fields.Integer(string="Id Nhanh.Vn", copy=False)
    check_data_odoo = fields.Boolean(string='Check dữ liệu từ odoo or Nhanh', default=True)
    width_product = fields.Float('Width', copy=False)
    height_product = fields.Float('Height', copy=False)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if not res.brand_id.id:
            return res
        self.synchronized_create_product(res)
        return res

    def synchronized_create_product(self, res):
        if res.check_data_odoo and res.brand_id.id:
            nhanh_configs = constant.get_nhanh_configs(self, brand_ids=[res.brand_id.id]).get(res.brand_id.id)
            if nhanh_configs.get('nhanh_connector.nhanh_app_id', '') or nhanh_configs.get(
                    'nhanh_connector.nhanh_business_id', '') or nhanh_configs.get('nhanh_connector.nhanh_access_token',
                                                                                  ''):

                data = [{
                    "id": res.id,
                    "name": res.name,
                    "code": res.barcode if res.barcode else '',
                    "barcode": res.barcode if res.barcode else '',
                    "importPrice": res.list_price,
                    "price": res.list_price,
                    "shippingWeight": res.weight * 1000,
                    "status": 'New'
                }]

                try:
                    res_server = self.post_data_nhanh(nhanh_configs, data)
                    status_nhanh = 1
                    res_json = res_server.json()
                    if status_nhanh == 1:
                        if res_json['code'] == 0:
                            res.write(
                                {
                                    'description': f'Sync Product error {res_json["messages"]}'
                                }
                            )
                            _logger.info(f'Sync Product error {res_json["messages"]}')
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
                    res.write(
                        {
                            'description': f'Sync Product error {ex}'
                        }
                    )
                    _logger.info(f'Sync Product from NhanhVn error {ex}')
        return True

    def write(self, vals):
        res = super().write(vals)
        if 'name' not in vals and 'barcode' not in vals and 'list_price' not in vals and 'weight' not in vals:
            return res
        data = []
        for item in self:
            if not item.nhanh_id:
                continue
            data.append({
                "id": item._origin.id,
                "idNhanh": item.nhanh_id,
                "name": item.name,
                "code": item.barcode if item.barcode else '',
                "barcode": item.barcode if item.barcode else '',
                "importPrice": item.list_price,
                "price": item.list_price,
                "shippingWeight": item.weight * 1000,
                "status": 'New'
            })
        if not data:
            return res
        self.synchronized_price_nhanh(data)
        return res

    def unlink(self):
        data = []
        for item in self:
            if not item.nhanh_id:
                continue
            data.append({
                "id": item._origin.id,
                "idNhanh": item.nhanh_id,
                "name": item.name,
                "code": item.barcode if item.barcode else '',
                "barcode": item.barcode if item.barcode else '',
                "importPrice": item.list_price,
                "price": item.list_price,
                "shippingWeight": item.weight * 1000,
                "status": 'Inactive'
            })
        if not data:
            return super().unlink()
        self.synchronized_price_nhanh(data)
        return super().unlink()

    def synchronized_price_nhanh(self, data):
        nhanh_configs = constant.get_nhanh_configs(self, brand_ids=[self.brand_id.id]).get(self.brand_id.id)
        if nhanh_configs.get('nhanh_connector.nhanh_app_id', '') or nhanh_configs.get(
                'nhanh_connector.nhanh_business_id', '') or nhanh_configs.get('nhanh_connector.nhanh_access_token', ''):
            status_nhanh = 1
            try:
                res_server = self.post_data_nhanh(nhanh_configs, data)
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

    def post_data_nhanh(self, configs, data):
        url = f"{constant.base_url()}/product/add"
        payload = {
            'version': '2.0',
            'appId': configs.get('nhanh_connector.nhanh_app_id', ''),
            'businessId': configs.get('nhanh_connector.nhanh_business_id', ''),
            'accessToken': configs.get('nhanh_connector.nhanh_access_token', ''),
            'data': json.dumps(data)
        }
        res_server = requests.post(url, data=payload)
        return res_server
