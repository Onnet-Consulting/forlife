# -*- coding: utf-8 -*-

from odoo.addons.nhanh_connector.models import constant
from odoo import _, models, fields, api
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    nhanh_id = fields.Char(string="Id Nhanh.Vn", copy=False)
    check_data_odoo = fields.Boolean(string='Check dữ liệu từ odoo or Nhanh', default=True)
    # width_product = fields.Float('Width', copy=False)
    # height_product = fields.Float('Height', copy=False)
    # weight = fields.Float('Weight', digits='Stock Weight', default=0.2)

    def get_nhanh_name(self):
        product_name = f"{self.name} {self.barcode}"

        # màu và size
        color_name = ','.join(
            self.attribute_line_ids.filtered(lambda v: v.attribute_id.name.upper() == "MÀU").value_ids.mapped('name')
        )
        size_name = ','.join(
            self.attribute_line_ids.filtered(lambda v: v.attribute_id.name.upper() == "SIZE").value_ids.mapped('name')
        )

        if color_name and not size_name:
            product_name = f"{product_name} ({color_name})"
        elif size_name and not color_name:
            product_name = f"{product_name} ({size_name})"
        elif size_name and color_name:
            product_name = f"{product_name} ({color_name} / {size_name})"
        return product_name

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        # if not res.brand_id.id or not res.categ_id.category_type_id.x_sync_nhanh:
        #     return res

        for line in res:
            if line.brand_id.id and line.categ_id.category_type_id.x_sync_nhanh:
                self.sudo().with_delay(
                    description="Sync product to NhanhVn", channel="root.NhanhMQ"
                ).synchronized_create_product(line)
            # self.synchronized_create_product(res)
        return res

    def get_pcpc_price_list_by_product(self, product_id):
        domain = [
            ('is_for_nhanh', '=', True), 
            ('program_id', '!=', False),
            ('product_tmpl_id', '=', product_id.id),
            ('state', '=', 'in_progress'),
            ('to_date', '>=', fields.Datetime.now()),
            ('from_date', '<=', fields.Datetime.now()),
        ]
        pl_res = self.env["promotion.pricelist.item"].sudo().search(domain, order="fixed_price ASC", limit=1)
        if pl_res:
            price = pl_res.fixed_price
        else:
            price = product_id.list_price
        return price

    def synchronized_create_product(self, res):
        if res.check_data_odoo and res.brand_id.id and res.categ_id.category_type_id.x_sync_nhanh:
            nhanh_config = constant.get_nhanh_configs(self, brand_ids=[res.brand_id.id]).get(res.brand_id.id)
            if nhanh_config.get('nhanh_connector.nhanh_app_id', '') \
                or nhanh_config.get('nhanh_connector.nhanh_business_id', '') \
                or nhanh_config.get('nhanh_connector.nhanh_access_token',''):

                price = self.get_pcpc_price_list_by_product(res)

                data = [{
                    "id": res.id,
                    "name": res.get_nhanh_name(),
                    "code": res.barcode if res.barcode else '',
                    "barcode": res.barcode if res.barcode else '',
                    "importPrice": res.list_price,
                    "price": price,
                    "shippingWeight": res.weight if res.weight > 0 else 200,
                    "status": 'New'
                }]

                try:
                    res_server = self.post_data_nhanh(nhanh_config, data)
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

        if vals.get("check_data_odoo"):
            return res

        fields_up = vals.keys()
        require_fields = [
            'name',
            'attribute_line_ids',
            'barcode',
            'list_price',
            'brand_id',
            'categ_id',
            'weight'
        ]

        last_fields = set(require_fields) - set(fields_up)
        if len(last_fields) == len(require_fields):
            return res
        data = []
        # is_create = False
        for item in self:
            if not item.nhanh_id:
                if item.brand_id.id and item.categ_id.category_type_id.x_sync_nhanh:
                    # is_create = True
                    self.sudo().with_delay(
                        description="Sync product to NhanhVn", channel="root.NhanhMQ"
                    ).synchronized_create_product(item)

            elif item.brand_id.id and item.categ_id.category_type_id.x_sync_nhanh:
                price = self.get_pcpc_price_list_by_product(item)

                data.append({
                    "id": item._origin.id,
                    "idNhanh": item.nhanh_id,
                    "name": item.get_nhanh_name(),
                    "code": item.barcode if item.barcode else '',
                    "barcode": item.barcode if item.barcode else '',
                    "importPrice": item.list_price,
                    "price": price,
                    "shippingWeight": item.weight if item.weight > 0 else 200,
                    "status": 'New'
                })

        if len(data):
            self.sudo().with_delay(
                description="Update & Sync product to NhanhVn", channel="root.NhanhMQ"
            ).synchronized_price_nhanh(data)
            # self.synchronized_price_nhanh(data)
        # if is_create:
        #     self.sudo().with_delay(
        #         description="Sync product to NhanhVn", channel="root.NhanhMQ"
        #     ).synchronized_create_product(self)
            # self.synchronized_create_product(self)
        
        return res

    def unlink(self):
        data = []
        for item in self:
            if not item.nhanh_id or not item.categ_id.category_type_id.x_sync_nhanh:
                continue
            data.append({
                "id": item._origin.id,
                "idNhanh": item.nhanh_id,
                "name": item.get_nhanh_name(),
                "code": item.barcode if item.barcode else '',
                "barcode": item.barcode if item.barcode else '',
                "importPrice": item.list_price,
                "price": item.list_price,
                "shippingWeight": item.weight if item.weight > 0 else 200,
                "status": 'Inactive'
            })
        if not data:
            return super().unlink()
        self.synchronized_price_nhanh(data)
        return super().unlink()

    def synchronized_price_nhanh(self, data):
        nhanh_config = constant.get_nhanh_configs(self, brand_ids=[self.brand_id.id]).get(self.brand_id.id)
        if nhanh_config.get('nhanh_connector.nhanh_app_id', '') or nhanh_config.get(
                'nhanh_connector.nhanh_business_id', '') or nhanh_config.get('nhanh_connector.nhanh_access_token', ''):
            status_nhanh = 1
            try:
                res_server = self.post_data_nhanh(nhanh_config, data)
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


    def synchronized_product_exists_nhanh(self, line, pl_list_price=False):
        if self.nhanh_id and self.brand_id.id and self.categ_id.category_type_id.x_sync_nhanh:
            data = []
            price = self.list_price
            if pl_list_price:
                price = line.fixed_price

            data.append({
                "id": self._origin.id,
                "idNhanh": self.nhanh_id,
                "name": self.get_nhanh_name(),
                "code": self.barcode if self.barcode else '',
                "barcode": self.barcode if self.barcode else '',
                "importPrice": self.list_price,
                "price": price,
                "shippingWeight": self.weight if self.weight > 0 else 200,
                "status": 'New'
            })
            self.sudo().with_delay(
                description="Update & Sync product to NhanhVn", channel="root.NhanhMQ"
            ).synchronized_price_nhanh(data)

