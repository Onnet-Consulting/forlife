# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

import psycopg2
import datetime
import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.nhanh_connector.models import constant
import requests
import base64
from urllib.request import urlopen

_logger = logging.getLogger(__name__)

NHANH_BASE_URL = 'https://open.nhanh.vn/api'


class SaleOrder(models.Model):
    _inherit = "sale.order"
    nhanh_status = fields.Char(string='Nhanh order status')
    nhanh_shipping_fee = fields.Float(string='Shipping fee')
    nhanh_sale_channel_id = fields.Integer(string='Sale channel id')

    def get_nhanh_configs(self):
        '''
        Get nhanh config from ir_config_parameter table
        '''
        params = self.env['ir.config_parameter'].search([('key', 'ilike', 'nhanh_connector.nhanh_')]).read(['key', 'value'])
        nhanh_configs = {}
        for param in params:
            nhanh_configs[param['key']] = param['value']
        return nhanh_configs

    @api.model
    def start_sync_order_from_nhanh(self):
        _logger.info("----------------Start Sync orders from NhanhVn --------------------")
        # Get datetime today and previous day
        today = datetime.datetime.today().strftime("%y/%m/%d")
        previous_day = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        _logger.info(f'Today is: {today}, Previous day is: {previous_day}')
        # Set up API information
        nhanh_configs = self.get_nhanh_configs()
        # Won't run if exist at least one empty param
        if 'nhanh_connector.nhanh_app_id' not in nhanh_configs or 'nhanh_connector.nhanh_business_id' not in nhanh_configs \
                or 'nhanh_connector.nhanh_access_token' not in nhanh_configs:
            _logger.info(f'Nhanh configuration does not set')
            return False
        query_params = {
            'data': "'{" + f'"fromDate":"{previous_day}","toDate":"{today}"' + "}'"
        }
        url = f"{NHANH_BASE_URL}/order/index?version=2.0&appId={constant.get_params(self)['appId']}" \
              f"&businessId={constant.get_params(self)['businessId']}&accessToken={constant.get_params(self)['accessToken']}" \
              f"&data={query_params['data']}"
        # Get all orders from previous day to today from Nhanh.vn
        try:
            res_server = requests.post(url)
            res = res_server.json()
        except Exception as ex:
            _logger.info(f'Get orders from NhanhVn error {ex}')
            return False
        if res['code'] == 0:
            _logger.info(f'Get order error {res["messages"]}')
            return False
        else:
            order_model = self.env['sale.order']
            partner_model = self.env['res.partner']
            nhanh_orders = res['data']['orders']
            nhanh_order_keys = list(nhanh_orders.keys())
            _logger.info(f'List order id from NhanhVN: {nhanh_order_keys}')
            # Get all odoo orders which don't exist in nhanhvn
            odoo_orders = order_model.sudo().search([('nhanh_id', 'in', nhanh_order_keys)]).read(
                ['nhanh_id'])
            odoo_order_ids = [str(x['nhanh_id']) for x in odoo_orders if x['nhanh_id'] != 0]
            # odoo_order_ids = ['217639118', '217639271', '217652613', '218324611']
            _logger.info(f'List order id from Odoo: {odoo_order_ids}')
            # Delete in nhanh_orders if it existed in odoo_orders
            for item in odoo_order_ids:
                if item in nhanh_orders:
                    nhanh_orders.pop(item)
            list(nhanh_orders)
            # _logger.info(nhanh_orders)
            for k, v in nhanh_orders.items():
                # Add customer if not existed
                partner = partner_model.sudo().search([('code_current_customers', '=', 'code_current_customers_nhanhvn')], limit=1)
                if not partner:
                    partner_value = {
                        'code_current_customers': 'code_current_customers_nhanhvn',
                        'name': 'Current customers Nhanh.Vn',
                    }
                    partner = partner_model.sudo().create(partner_value)
                order_line = []
                uom = self.env.ref('uom.product_uom_unit').id

                for item in v['products']:
                    product = self.search_product(('nhanh_id', '=', item.get('productId')))
                    if not product and item.get('productBarcode'):
                        product = self.search_product(('barcode', '=', item.get('productBarcode')))
                    if not product and item.get('productCode'):
                        product = self.search_product(('code_product', '=', item.get('productCode')))
                    if not product:
                         product = self.env['product.template'].create({
                            'detailed_type': 'asset',
                            'nhanh_id': item.get('productId'),
                            'check_data_odoo': False,
                            'name': item.get('productName'),
                            'barcode': item.get('productBarcode'),
                            'code_product': item.get('productCode'),
                            'list_price': item.get('price'),
                            'uom_id': uom,
                            'weight': item.get('shippingWeight', 0),

                        })
                    product_product = self.env['product.product'].search([('product_tmpl_id', '=', product.id)], limit=1)
                    order_line.append((
                        0, 0,
                        {'product_template_id': product.id, 'product_id': product_product.id, 'name': product.name,
                         'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
                         'product_uom': product.uom_id.id if product.uom_id else uom,
                         'customer_lead': 0, 'sequence': 10, 'is_downpayment': False,
                         'discount': item.get('discount')}))
                # Add orders  to odoo
                _logger.info(v)
                status = 'draft'
                if v['statusCode'] == 'confirmed':
                    status = 'draft'
                elif v['statusCode'] in ['Packing', 'Pickup']:
                    status = 'sale'
                elif v['statusCode'] in ['Shipping', 'Returning']:
                    status = 'sale'
                elif v['statusCode'] == 'success':
                    status = 'done'
                elif v['statusCode'] == 'canceled':
                    status = 'cancel'

                value = {
                    'nhanh_id': v['id'],
                    'nhanh_status': v['statusCode'],
                    'partner_id': partner.id,
                    'nhanh_shipping_fee': v['shipFee'],
                    'nhanh_sale_channel_id': v['saleChannel'],
                    'source_record': True,
                    'state': status,
                    'code_coupon': v['couponCode'],
                    'name_customer': v['customerName'],
                    'note': v['privateDescription'],
                    'order_line': order_line
                }
                order_model.sudo().create(value)
                _logger.info("----------------Sync orders from NhanhVn done--------------------")

    @api.model
    def start_sync_customer_from_nhanh(self):
        ## Danh sách khách hàng
        _logger.info("----------------Start Sync customer from NhanhVn --------------------")

        today = datetime.datetime.today().strftime("%y/%m/%d")
        previous_day = (datetime.datetime.today() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
        _logger.info(f'Today is: {today}, Previous day is: {previous_day}')
        ## Check tồn tại data url
        nhanh_configs = self.get_nhanh_configs()
        if 'nhanh_connector.nhanh_app_id' not in nhanh_configs or 'nhanh_connector.nhanh_business_id' not in nhanh_configs \
                or 'nhanh_connector.nhanh_access_token' not in nhanh_configs:
            _logger.info(f'Nhanh configuration does not set')
            return False
        data = "'{" + f'"fromDate":"{previous_day}","toDate":"{today}"' + "}'"
        query_params = {
            'data': data
        }

        list_number_phone = list(self.env['res.partner'].search([]).mapped('phone'))
        url = self.get_link_nhanh('customer', 'search', query_params['data'])
        if url:
            status_post = 1
            try:
                res_server = requests.post(url)
                res = res_server.json()
            except Exception as ex:
                status_post = 0
                _logger.info(f'Get customer from NhanhVn error {ex}')
                return False
            if status_post == 1:
                if res['code'] == 0:
                    _logger.info(f'Get customer error {res["messages"]}')
                    return False
                else:
                    for item in res.get('data').get('customers'):
                        if res.get('data').get('customers').get(item).get('mobile') not in list_number_phone:
                            value_data = res.get('data').get('customers').get(item)

                            self.env['res.partner'].create({
                                'source_record': True,
                                'name': value_data.get('name'),
                                'phone': value_data.get('mobile'),
                                'email': value_data.get('email'),
                                'gender': 'male' if value_data.get('gender') == '1' else 'female' if value_data.get('gender') == '2' else False,
                                'contact_address_complete': value_data.get('address'),
                                'street': value_data.get('address'),
                                'vat': value_data.get('taxCode'),
                                'date_of_birth': datetime.datetime.strptime(value_data.get('birthday'), "%Y-%m-%d").date() if value_data.get('birthday') else False,
                                'type_customer': 'retail_customers' if value_data.get(
                                    'type') == 1 else 'wholesalers' if value_data.get(
                                    'type') == 2 else 'agents' if value_data.get('type') == 2 else False,
                            })
        ## End

    @api.model
    def start_sync_product_from_nhanh(self):
        # Cập nhật danh mục trước khi tạo product
        self.data_product_category_nhanh()
        ## Danh sách sản phẩm
        _logger.info("----------------Start Sync product from NhanhVn --------------------")

        today = datetime.datetime.today().strftime("%y/%m/%d")
        previous_day = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        _logger.info(f'Today is: {today}, Previous day is: {previous_day}')
        ## Check tồn tại data url
        nhanh_configs = self.get_nhanh_configs()
        if 'nhanh_connector.nhanh_app_id' not in nhanh_configs or 'nhanh_connector.nhanh_business_id' not in nhanh_configs \
                or 'nhanh_connector.nhanh_access_token' not in nhanh_configs:
            _logger.info(f'Nhanh configuration does not set')
            return False,
        query_params = {
            'data': "'{" + f'"fromDate":"{previous_day}","toDate":"{today}"' + "}'"
        }
        try:
            res_server = requests.post(self.get_link_nhanh('product', 'search', query_params['data']))
            status_post = 1
            res = res_server.json()
        except Exception as ex:
            status_post = 0
            _logger.info(f'Get product from NhanhVn error {ex}')
            return False
        if status_post == 1:
            if res['code'] == 0:
                _logger.info(f'Get product error {res["messages"]}')
                return False
            else:
                for item in res.get('data').get('products'):
                    value_data = res.get('data').get('products').get(item)
                    category = False
                    if value_data and value_data.get('code'):
                        if value_data.get('categoryId'):
                            category = self.env['product.category'].search([('nhanh_product_category_id', '=', value_data.get('categoryId'))])
                        product = self.search_product(('nhanh_id', '=', value_data.get('idNhanh')))
                        if not product and res.get('data').get('products').get(item).get('barcode'):
                           product = self.search_product(('barcode', '=', value_data.get('barcode')))
                        if not product and value_data.get('code'):
                           product = self.search_product(('code_product', '=', value_data.get('code')))
                        if not product:
                            dic_data_product = {
                                'nhanh_id': value_data.get('idNhanh'),
                                'check_data_odoo': False,
                                'name': value_data.get('name'),
                                'barcode': value_data.get('barcode'),
                                'code_product': value_data.get('code'),
                                'list_price': value_data.get('price'),
                                'detailed_type': 'asset',
                            }
                            if category:
                                dic_data_product.update({'categ_id': category.id})
                            self.env['product.template'].create(dic_data_product)
                    else:
                        _logger.info(f'Get product from NhanhVn error')
        ## End

    @api.model
    def start_sync_product_category_from_nhanh(self):
        _logger.info("----------------Start Sync Product Category from NhanhVn --------------------")
        self.data_product_category_nhanh()

    def data_product_category_nhanh(self):
        today = datetime.datetime.today().strftime("%y/%m/%d")
        previous_day = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        _logger.info(f'Today is: {today}, Previous day is: {previous_day}')
        nhanh_configs = self.get_nhanh_configs()
        if 'nhanh_connector.nhanh_app_id' not in nhanh_configs or 'nhanh_connector.nhanh_business_id' not in nhanh_configs \
                or 'nhanh_connector.nhanh_access_token' not in nhanh_configs:
            _logger.info(f'Nhanh configuration does not set')
            return False,
        query_params = {
            'data': "'{" + f'"fromDate":"{previous_day}","toDate":"{today}"' + "}'"
        }
        try:
            res_server = requests.post(self.get_link_nhanh('product', 'category', query_params['data']))
            status_post = 1
            res = res_server.json()
        except Exception as ex:
            status_post = 0
            _logger.info(f'Get orders from NhanhVn error {ex}')
            return False
        if status_post == 1:
            if res['code'] == 0:
                _logger.info(f'Get order error {res["messages"]}')
                return False
            else:
                self.create_product_category(res['data'])

    def create_product_category(self, data, parent_id=None):
        for category in data:
            product_category = self.env['product.category'].search([('code_category', '=', str(category['code']))])
            if not product_category:
                new_category = self.env['product.category'].create({
                    'code_category': category.get('code'),
                    'name': category.get('name'),
                    'nhanh_parent_id': category.get('parentId'),
                    'nhanh_product_category_id': category.get('id'),
                    'content_category': category.get('content'),
                    'parent_id': parent_id,
                })
                if 'childs' in category :
                    self.create_product_category(category['childs'], new_category.id)
            else:
                product_category.write({'parent_id': parent_id})
                if 'childs' in category:
                    self.create_product_category(category['childs'], product_category.id)
        return True

    def get_link_nhanh(self, category, type_get, data):
        nhanh_configs = self.get_nhanh_configs()
        if 'nhanh_connector.nhanh_app_id' not in nhanh_configs or 'nhanh_connector.nhanh_business_id' not in nhanh_configs \
                or 'nhanh_connector.nhanh_access_token' not in nhanh_configs:
            _logger.info(f'Nhanh configuration does not set')
            return False
        url = f"{constant.base_url()}/{category}/{type_get}?version={constant.get_params(self)['version']}&appId={constant.get_params(self)['appId']}" \
              f"&businessId={constant.get_params(self)['businessId']}&accessToken={constant.get_params(self)['accessToken']}" \
              f"&data={data}"
        return url

    def search_product(self, domain_product):
        return self.env['product.template'].search([domain_product])
