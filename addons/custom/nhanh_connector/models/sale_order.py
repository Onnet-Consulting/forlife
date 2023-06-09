# -*- coding: utf-8 -*-
from odoo.addons.nhanh_connector.models import constant
from odoo import api, fields, models, _
import json

import datetime
import logging
import requests

_logger = logging.getLogger(__name__)

NHANH_BASE_URL = 'https://open.nhanh.vn/api'


class SaleOrderNhanh(models.Model):
    _inherit = 'sale.order'

    nhanh_id = fields.Integer(string='Id Nhanh.vn', copy=False)
    nhanh_origin_id = fields.Integer(string='Id đơn gốc Nhanh.vn', copy=False)
    numb_action_confirm = fields.Integer(default=0)
    source_record = fields.Boolean(string="Đơn hàng từ nhanh", default=False)
    code_coupon = fields.Char(string="Mã coupon")
    name_customer = fields.Char(string='Tên khách hàng mới')
    note_customer = fields.Text(string='Ghi chú khách hàng')
    order_partner_id = fields.Many2one('res.partner', 'Khách Order')
    carrier_name = fields.Char('Carrier Name')

    nhanh_status = fields.Char(string='Nhanh order status')
    nhanh_shipping_fee = fields.Float(string='Shipping fee')
    nhanh_customer_shipping_fee = fields.Float(string='Customer Shipping fee')
    nhanh_sale_channel_id = fields.Integer(string='Sale channel id')
    nhanh_order_status = fields.Selection([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
        ('packing', 'Packing'),
        ('pickup', 'Pickup'),
        ('shipping', 'Shipping'),
        ('returning', 'Returning'),
        ('success', 'Success'),
        ('canceled', 'Canceled'),
    ], 'Nhanh status')

    # def write(self, vals):
    #     res = super().write(vals)
    #     for rec in self:
    #         if 'state' in vals and rec.nhanh_id:
    #             self.synchronized_price_nhanh(rec.state, rec)
    #     return res
    #
    # def synchronized_price_nhanh(self, odoo_st, rec):
    #     status = 'Confirming'
    #     if odoo_st == 'draft':
    #         status = 'Confirmed'
    #     elif odoo_st == 'send':
    #         status = 'Confirming'
    #     elif odoo_st == 'sale':
    #         status = 'Confirmed'
    #     elif odoo_st == 'done':
    #         status = 'Success'
    #     elif odoo_st == 'cancel':
    #         status = 'Canceled'
    #     try:
    #         res_server = constant.get_post_status(self, status, rec)
    #     except Exception as ex:
    #         _logger.info(f'Get orders from NhanhVn error {ex}')
    #         return False
    #     return True

    @api.model
    def start_sync_order_from_nhanh(self):
        _logger.info("----------------Start Sync orders from NhanhVn --------------------")
        # Get datetime today and previous day
        today = datetime.datetime.today().strftime("%y-%m-%d")
        previous_day = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        _logger.info(f'Today is: {today}, Previous day is: {previous_day}')
        # Set up API information
        nhanh_configs = constant.get_nhanh_configs(self)
        for brand_id in self.env['res.brand'].sudo().search([]):
            nhanh_config = nhanh_configs.get(brand_id.id, {})
            if not nhanh_config:
                continue
            # Won't run if exist at least one empty param
            if 'nhanh_connector.nhanh_app_id' not in nhanh_config or 'nhanh_connector.nhanh_business_id' not in nhanh_config \
                    or 'nhanh_connector.nhanh_access_token' not in nhanh_config:
                _logger.info(f'Nhanh configuration does not set')
                continue
            data = {
                "fromDate": previous_day,
                "toDate": today,
            }
            url = f"{NHANH_BASE_URL}/order/index?version=2.0&appId={nhanh_config.get('nhanh_connector.nhanh_app_id', '')}" \
                  f"&businessId={nhanh_config.get('nhanh_connector.nhanh_business_id', '')}&accessToken={nhanh_config.get('nhanh_connector.nhanh_access_token', '')}"
            # Get all orders from previous day to today from Nhanh.vn
            try:
                res_server = requests.post(url, json=json.dumps(data))
                res = res_server.json()
            except Exception as ex:
                _logger.info(f'Get orders from NhanhVn error {ex}')
                continue
            if res['code'] == 0:
                _logger.info(f'Get order error {res["messages"]}')
                continue
            order_model = self.env['sale.order']
            partner_model = self.env['res.partner']
            data = res.get('data')
            for page in range(1, data.get('totalRecords') + 1):
                data['page'] = page
                res_server = requests.post(url, json=json.dumps(data))
                res = res_server.json()
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
                name_customer = False
                # Add customer if not existed
                nhanh_partner = partner_model.sudo().search(
                    [('code_current_customers', '=', 'code_current_customers_nhanhvn')], limit=1)
                if not nhanh_partner:
                    nhanh_partner = partner_model.sudo().create({
                        'code_current_customers': 'code_current_customers_nhanhvn',
                        'name': 'Nhanh.Vn',
                        'customer_rank': 1
                    })
                partner = partner_model.sudo().search(
                    ['|', ('mobile', '=', v['customerMobile']), ('phone', '=', v['customerMobile'])], limit=1)
                if partner:
                    name_customer = v['customerName']
                if not partner:
                    partner_value = {
                        'phone': v['customerMobile'],
                        'mobile': v['customerMobile'],
                        'name': v['customerName'],
                        'email': v['customerEmail'],
                        'contact_address_complete': v['customerAddress'],
                        'customer_nhanh_id': v['customerId'],
                    }
                    partner = partner_model.sudo().create(partner_value)
                order_line = []
                uom = self.env.ref('uom.product_uom_unit').id
                location_id = self.env['stock.location'].search([('nhanh_id', '=', int(v['depotId']))], limit=1)

                for item in v['products']:
                    product = self.search_product(('nhanh_id', '=', item.get('productId')))
                    if not product and item.get('productBarcode'):
                        product = self.search_product(('barcode', '=', item.get('productBarcode')))
                    if not product and item.get('productCode'):
                        product = self.search_product(('barcode', '=', item.get('productCode')))
                    if not product:
                        product = self.env['product.template'].create({
                            'detailed_type': 'asset',
                            'nhanh_id': item.get('productId'),
                            'check_data_odoo': False,
                            'name': item.get('productName'),
                            'barcode': item.get('productBarcode'),
                            # 'code_product': item.get('productCode'),
                            'list_price': item.get('price'),
                            'uom_id': uom,
                            'weight': item.get('shippingWeight', 0),
                            'responsible_id': None
                        })
                    product_product = self.env['product.product'].search([('product_tmpl_id', '=', product.id)],
                                                                         limit=1)
                    order_line.append((
                        0, 0,
                        {'product_template_id': product.id, 'product_id': product_product.id, 'name': product.name,
                         'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
                         'product_uom': product.uom_id.id if product.uom_id else uom,
                         'customer_lead': 0, 'sequence': 10, 'is_downpayment': False,
                         'x_location_id': location_id.id if location_id else None,
                         'discount': float(item.get('discount')) / float(item.get('price')) * 100 if item.get(
                             'discount') else 0,
                         'x_cart_discount_fixed_price': float(item.get('discount')) * float(
                             item.get('quantity')) if item.get('discount') else 0}))
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

                # nhân viên kinh doanh
                user_id = self.env['res.users'].search([('partner_id.name', '=', v['saleName'])], limit=1)
                # đội ngũ bán hàng
                team_id = self.env['crm.team'].search([('name', '=', v['trafficSourceName'])], limit=1)
                default_company_id = self.env['res.company'].sudo().search([('code', '=', '1300')], limit=1)
                warehouse_id = self.env['stock.warehouse'].search([('nhanh_id', '=', int(v['depotId']))], limit=1)
                if not warehouse_id:
                    warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', default_company_id.id)],
                                                                      limit=1)
                value = {
                    'nhanh_id': v['id'],
                    'nhanh_status': v['statusCode'],
                    'partner_id': nhanh_partner.id,
                    'order_partner_id': partner.id,
                    'nhanh_shipping_fee': v['shipFee'],
                    'nhanh_customer_shipping_fee': v['customerShipFee'],
                    'nhanh_sale_channel_id': v['saleChannel'],
                    'source_record': True,
                    'state': status,
                    'code_coupon': v['couponCode'],
                    'name_customer': name_customer,
                    'note': v['privateDescription'],
                    'note_customer': v['description'],
                    'x_sale_chanel': 'online',
                    'carrier_name': v['carrierName'],
                    'user_id': user_id.id if user_id else None,
                    'team_id': team_id.id if team_id else None,
                    'company_id': default_company_id.id if default_company_id else None,
                    'warehouse_id': location_id.warehouse_id.id if location_id and location_id.warehouse_id  else None,
                    'order_line': order_line
                }
                # đổi hàng
                if v.get('returnFromOrderId', 0):
                    origin_order_id = self.env['sale.order'].sudo().search(
                        [('nhanh_id', '=', v.get('returnFromOrderId', 0))], limit=1)
                    value.update({
                        'x_is_return': True,
                        'x_origin': origin_order_id.id if origin_order_id else None,
                        'nhanh_origin_id': v.get('returnFromOrderId', 0)
                    })
                order_model.sudo().create(value)
                _logger.info("----------------Sync orders from NhanhVn done--------------------")

    @api.model
    def start_sync_customer_from_nhanh(self):
        ## Danh sách khách hàng
        _logger.info("----------------Start Sync customer from NhanhVn --------------------")

        today = datetime.datetime.today().strftime("%Y-%m-%d")
        previous_day = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        _logger.info(f'Today is: {today}, Previous day is: {previous_day}')
        ## Check tồn tại data url
        nhanh_configs = constant.get_nhanh_configs(self)
        for brand_id in self.env['res.brand'].sudo().search([]):
            nhanh_config = nhanh_configs.get(brand_id.id, {})
            if not nhanh_config:
                continue
            if 'nhanh_connector.nhanh_app_id' not in nhanh_config or 'nhanh_connector.nhanh_business_id' not in nhanh_config \
                    or 'nhanh_connector.nhanh_access_token' not in nhanh_config:
                _logger.info(f'Nhanh configuration does not set')
                continue

            url = f"https://open.nhanh.vn/api/customer/search?version=2.0&appId={nhanh_config.get('nhanh_connector.nhanh_app_id','')}&businessId={nhanh_config.get('nhanh_connector.nhanh_business_id','')}&accessToken={nhanh_config.get('nhanh_connector.nhanh_access_token','')}"

            data = {
                "fromDate": previous_day,
                "toDate": today,
            }
            status_post = 1
            try:
                res_server = requests.post(url, json=json.dumps(data))
                res = res_server.json()
            except Exception as ex:
                status_post = 0
                _logger.info(f'Get customer from NhanhVn error {ex}')
                continue
            if status_post == 1:
                if res['code'] == 0:
                    _logger.info(f'Get customer error {res["messages"]}')
                    continue
                else:
                    data = res.get('data')
                    for page in range(1, data.get('totalPages') + 1):
                        data['page'] = page
                        res_server = requests.post(url, json=json.dumps(data))
                        res = res_server.json()
                        customers = res.get('data').get('customers')
                        for item in customers:
                            if not customers.get(item).get('mobile'):
                                continue
                            exist_partner = self.env['res.partner'].search_count(
                                [('phone', '=', customers.get(item).get('mobile'))])
                            if exist_partner:
                                continue
                            value_data = customers.get(item)

                            self.env['res.partner'].create({
                                'source_record': True,
                                'customer_nhanh_id': int(customers.get(item).get('id')),
                                'name': value_data.get('name'),
                                'phone': value_data.get('mobile'),
                                'mobile': value_data.get('mobile'),
                                'email': value_data.get('email'),
                                'gender': 'male' if value_data.get('gender') == '1' else 'female' if value_data.get(
                                    'gender') == '2' else 'other',
                                'contact_address_complete': value_data.get('address'),
                                'street': value_data.get('address'),
                                'vat': value_data.get('taxCode'),
                                'birthday': datetime.datetime.strptime(value_data.get('birthday'),
                                                                       "%Y-%m-%d").date() if value_data.get(
                                    'birthday') else None,
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
        nhanh_configs = constant.get_nhanh_configs(self)
        for brand_id in self.env['res.brand'].sudo().search([]):
            nhanh_config = nhanh_configs.get(brand_id.id, {})
            if not nhanh_config:
                continue
            if 'nhanh_connector.nhanh_app_id' not in nhanh_config or 'nhanh_connector.nhanh_business_id' not in nhanh_config \
                    or 'nhanh_connector.nhanh_access_token' not in nhanh_config:
                _logger.info(f'Nhanh configuration does not set')
                continue
            data = {
                "fromDate": previous_day,
                "toDate": today,
            }
            url = f"https://open.nhanh.vn/api/product/search?version=2.0&appId={nhanh_config.get('nhanh_connector.nhanh_app_id','')}&businessId={nhanh_config.get('nhanh_connector.nhanh_business_id','')}&accessToken={nhanh_config.get('nhanh_connector.nhanh_access_token','')}"

            try:
                res_server = requests.post(url, json.dumps(data))
                status_post = 1
                res = res_server.json()
            except Exception as ex:
                status_post = 0
                _logger.info(f'Get product from NhanhVn error {ex}')
                continue
            if status_post == 1:
                if res['code'] == 0:
                    _logger.info(f'Get product error {res["messages"]}')
                    continue
                for item in res.get('data').get('products'):
                    value_data = res.get('data').get('products').get(item)
                    category = False
                    if value_data and value_data.get('code'):
                        if value_data.get('categoryId'):
                            category = self.env['product.category'].search(
                                [('nhanh_product_category_id', '=', value_data.get('categoryId'))])
                        product = self.search_product(('nhanh_id', '=', value_data.get('idNhanh')))
                        if not product and res.get('data').get('products').get(item).get('barcode'):
                            product = self.search_product(('barcode', '=', value_data.get('barcode')))
                        if not product and value_data.get('code'):
                            product = self.search_product(('barcode', '=', value_data.get('code')))
                        if not product:
                            dic_data_product = {
                                'nhanh_id': value_data.get('idNhanh'),
                                'check_data_odoo': False,
                                'name': value_data.get('name'),
                                'barcode': value_data.get('barcode'),
                                # 'code_product': value_data.get('code'),
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
        today = datetime.datetime.today().strftime("%y/%m/%d")
        previous_day = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        _logger.info(f'Today is: {today}, Previous day is: {previous_day}')
        nhanh_configs = constant.get_nhanh_configs(self)
        for brand_id in self.env['res.brand'].sudo().search([]):
            nhanh_config = nhanh_configs.get(brand_id.id, {})
            if not nhanh_config:
                continue
            if 'nhanh_connector.nhanh_app_id' not in nhanh_config or 'nhanh_connector.nhanh_business_id' not in nhanh_config \
                    or 'nhanh_connector.nhanh_access_token' not in nhanh_config:
                _logger.info(f'Nhanh configuration does not set')
                continue
            data = {
                "fromDate": previous_day,
                "toDate": today,
            }
            url = f"https://open.nhanh.vn/api/product/category?version=2.0&appId={nhanh_config.get('nhanh_connector.nhanh_app_id', '')}&businessId={nhanh_config.get('nhanh_connector.nhanh_business_id', '')}&accessToken={nhanh_config.get('nhanh_connector.nhanh_access_token', '')}"

            try:
                res_server = requests.post(url, data=json.dumps(data))
                status_post = 1
                res = res_server.json()
            except Exception as ex:
                status_post = 0
                _logger.info(f'Get orders from NhanhVn error {ex}')
                continue
            if status_post == 1:
                if res['code'] == 0:
                    _logger.info(f'Get order error {res["messages"]}')
                    continue
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
                if 'childs' in category:
                    self.create_product_category(category['childs'], new_category.id)
            else:
                product_category.write({'parent_id': parent_id})
                if 'childs' in category:
                    self.create_product_category(category['childs'], product_category.id)
        return True

    def search_product(self, domain_product):
        return self.env['product.template'].search([domain_product])
