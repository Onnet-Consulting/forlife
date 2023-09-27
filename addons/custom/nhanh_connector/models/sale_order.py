# -*- coding: utf-8 -*-
from odoo.addons.nhanh_connector.models import constant
from odoo.addons.nhanh_connector.controllers.utils import NhanhClient
from odoo import api, fields, models, _
from odoo.tests import Form
import json

import datetime
import logging
import requests

_logger = logging.getLogger(__name__)

NHANH_BASE_URL = 'https://open.nhanh.vn/api'


class SaleOrderNhanh(models.Model):
    _inherit = 'sale.order'

    nhanh_id = fields.Char(string='Id Nhanh.vn', copy=False)
    nhanh_origin_id = fields.Char(string='Id đơn gốc Nhanh.vn', copy=False)
    numb_action_confirm = fields.Integer(default=0)
    source_record = fields.Boolean(string="Đơn hàng từ nhanh", default=False)
    code_coupon = fields.Char(string="Mã coupon")
    name_customer = fields.Char(string='Tên khách hàng mới')
    note_customer = fields.Text(string='Ghi chú khách hàng')
    order_partner_id = fields.Many2one('res.partner', 'Khách Order')
    # carrier_name = fields.Char('Carrier Name')

    nhanh_shipping_fee = fields.Float(string='Shipping fee')
    nhanh_customer_shipping_fee = fields.Float(string='Customer Shipping fee')
    nhanh_customer_phone = fields.Char(string='SDT Khách hàng')
    nhanh_sale_channel_id = fields.Integer(string='Sale channel id')
    nhanh_order_status = fields.Selection([
        ('new', 'Đơn mới'),
        ('confirming', 'Đang xác nhận'),
        ('customerconfirming', 'Chờ khách xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('packing', 'Đang đóng gói'),
        ('packed', 'Đã đóng gói'),
        ('changedepot', 'Đổi kho xuất hàng'),
        ('pickup', 'Chờ thu gom'),
        ('shipping', 'Đang chuyển'),
        ('success', 'Thành công'),
        ('failed', 'Thất bại'),
        ('canceled', 'Khách hủy'),
        ('aborted', 'Hệ thống hủy'),
        ('carriercanceled', 'Hãng vận chuyển hủy đơn'),
        ('soldout', 'Hết hàng'),
        ('returning', 'Đang chuyển hoàn'),
        ('returned', 'Đã chuyển hoàn')
    ], 'Nhanh status')
    delivery_carrier_id = fields.Many2one('delivery.carrier', 'Delivery Carrier')
    x_voucher = fields.Float(string='Giá trị voucher (Nhanh)')
    x_code_voucher = fields.Char(string="Mã voucher/code (Nhanh)")
    x_is_change = fields.Boolean(string="Đơn đổi hàng")
    nhanh_return_id = fields.Char(string='Id đơn trả Nhanh.vn', copy=False)
    x_transfer_code = fields.Char(string='Mã vận đơn', copy=False)
    sale_channel_id = fields.Many2one('sale.channel', 'Kênh / Sàn')

    def open_nhanh(self):
        storeId = self.x_location_id.warehouse_id.brand_id.code == 'FMT' and '92411' or '92405'
        return {
            'type': 'ir.actions.act_url',
            'url': "https://new.nhanh.vn/order/manage/detail?storeId=%s&id=%s"
                   % (storeId, self.nhanh_id),
            'target': 'new',
        }


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

    def create_an_order(self, order, brand_id):
        n_client = NhanhClient(self, constant)
        default_company_id = n_client.get_company()
        if not default_company_id:
            raise Exception ('Chọn company trước khi đồng bộ đơn hàng từ Nhanh.Vn, Vui lòng vào Thiết lập -> Kế toán để chọn company')

        location_id = n_client.get_location_by_company(default_company_id, int(order['depotId']))

        nhanh_origin_id = order.get('returnFromOrderId', 0)


        name_customer = False
        # Add customer if not existed
        nhanh_partner = n_client.get_nhanh_partner()

        partner_group_id = n_client.get_partner_group()

        partner = n_client.get_res_partner(partner_group_id, order)
        if partner:
            name_customer = order['customerName']
            if not n_client.check_customer_exists_store_first_order(partner):
                if location_id and location_id.warehouse_id:
                    n_client.create_store_first_order_for_customer(
                        partner, int(order['depotId'])
                    )

        if not partner:
            list_customers = constant.get_customers_from_nhanh(self, brand_id=brand_id.id, data={"mobile": order['customerMobile']})
            customer = list_customers.get(str(order['customerId']))
            partner = n_client.create_res_partner(order, brand_id, partner_group_id, customer)
            if location_id and location_id.warehouse_id:
                n_client.create_store_first_order_for_customer(
                    partner, int(order['depotId'])
                )

        order_line = n_client.get_order_line(order, brand_id, location_id, nhanh_partner, is_create=False)

        order_data = n_client.get_order_data(
            order, nhanh_partner, partner, name_customer, default_company_id, location_id
        )
        order_data["order_line"] = order_line
        
        x_voucher, x_code_voucher = n_client.order_paid_online(order)

        order_data.update({
            "x_voucher": x_voucher,
            "x_code_voucher": x_code_voucher
        })

        return_changed = n_client.order_return_and_changed(order)
        if return_changed:
            order_data.update(return_changed)

        if nhanh_origin_id:
            order_data.update({
                'x_is_return': True,
                'x_origin': None,
                'nhanh_origin_id': nhanh_origin_id
            })

        new_order = self.env['sale.order'].sudo().create(order_data)
        if order['statusCode'] in ["Packing", "Pickup", "Shipping", "Success", "Packed", "Returned"]:
            new_order.check_sale_promotion()
            if new_order.state != 'check_promotion' and not new_order.picking_ids and not nhanh_origin_id:
                try:
                    new_order.action_create_picking()
                except Exception as e:
                    raise e
            
        if order['statusCode'] in ['Canceled', 'Aborted', 'CarrierCanceled']:
            if new_order.picking_ids:
                for picking_id in new_order.picking_ids:
                    if picking_id.state != 'done':
                        picking_id.action_cancel()


    @api.model
    def start_sync_order_from_nhanh(self, *args, **kwargs):
        _logger.info("----------------Start Sync orders from NhanhVn --------------------")
        today = datetime.datetime.today().strftime("%Y-%m-%d")
        previous_day = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        if not kwargs.get("toDate"):
            kwargs["toDate"] = today

        if not kwargs.get("fromDate"):
            kwargs["fromDate"] = previous_day

        order_model = self.env['sale.order']
        odoo_orders = order_model.sudo().search(
            ['|', ('nhanh_id', '!=', False), ('nhanh_id', '!=', 0)]
        ).read(['nhanh_id'])

        odoo_order_ids = [str(x['nhanh_id']) for x in odoo_orders if x['nhanh_id'] != 0]

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

            url = f"{NHANH_BASE_URL}/order/index"
            data = {
                "version": 2.0,
                "appId": '%s' % nhanh_config.get('nhanh_connector.nhanh_app_id', 0),
                "businessId": '%s' % nhanh_config.get('nhanh_connector.nhanh_business_id', 0),
                "accessToken": nhanh_config.get('nhanh_connector.nhanh_access_token', ''),
                "data": json.dumps(kwargs)
            }
            # Get all orders from previous day to today from Nhanh.vn
            try:
                res_server = requests.post(url, data=data)
                res = res_server.json()
            except Exception as ex:
                _logger.info(f'Get orders from NhanhVn error {ex}')
                continue
            if res['code'] == 0:
                _logger.info(f'Get order error {res["messages"]}')
                continue

            res_data = res.get('data')
            nhanh_orders = res['data']['orders']

            for page in range(2, res_data.get('totalPages') + 1):
                kwargs['page'] = page
                data["data"] = json.dumps(kwargs)
                try:
                    res_page_server = requests.post(url, data=data)
                    res_page_data = res_page_server.json()
                    nhanh_orders.update(res_page_data['data']['orders'])
                except Exception as e:
                    _logger.info(str(e))
                    pass

            for item in odoo_order_ids:
                if nhanh_orders.get(item):
                    nhanh_orders.pop(item)

            for oid, order in nhanh_orders.items():
                self.sudo().with_delay(
                    description="Sync order from NhanhVn to Odoo", channel="root.NhanhMQ"
                ).create_an_order(order, brand_id)
        # # Get datetime today and previous day
        # today = datetime.datetime.today().strftime("%Y-%m-%d")
        # previous_day = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        # _logger.info(f'Today is: {today}, Previous day is: {previous_day}')
        # # Set up API information
        # nhanh_configs = constant.get_nhanh_configs(self)
        # partner_group_id = self.env['res.partner.group'].sudo().search([('code', '=', 'C')], limit=1)

        # uom = self.env.ref('uom.product_uom_unit').id

        # order_model = self.env['sale.order']
        # partner_model = self.env['res.partner']

        # # Add customer if not existed
        # nhanh_partner = partner_model.sudo().search(
        #     [('code_current_customers', '=', 'code_current_customers_nhanhvn')], limit=1)
        # if not nhanh_partner:
        #     nhanh_partner = partner_model.sudo().create({
        #         'code_current_customers': 'code_current_customers_nhanhvn',
        #         'name': 'Nhanh.Vn',
        #         'customer_rank': 1
        #     })

        # location_ids = self.env['stock.location'].search([('nhanh_id', '!=', False)])

        # product = self.search_product([])

        # odoo_orders = order_model.sudo().search(
        #     ['|', ('nhanh_id', '!=', False), ('nhanh_id', '!=', 0)]
        # ).read(['nhanh_id'])

        # odoo_order_ids = [str(x['nhanh_id']) for x in odoo_orders if x['nhanh_id'] != 0]

        # for brand_id in self.env['res.brand'].sudo().search([]):
        #     nhanh_config = nhanh_configs.get(brand_id.id, {})
        #     if not nhanh_config:
        #         continue
        #     # Won't run if exist at least one empty param
        #     if 'nhanh_connector.nhanh_app_id' not in nhanh_config or 'nhanh_connector.nhanh_business_id' not in nhanh_config \
        #             or 'nhanh_connector.nhanh_access_token' not in nhanh_config:
        #         _logger.info(f'Nhanh configuration does not set')
        #         continue
        #     kwargs.update({
        #         "fromDate": previous_day,
        #         "toDate": today,
        #     })
        #     url = f"{NHANH_BASE_URL}/order/index"
        #     data = {
        #         "version": 2.0,
        #         "appId": '%s' % nhanh_config.get('nhanh_connector.nhanh_app_id', 0),
        #         "businessId": '%s' % nhanh_config.get('nhanh_connector.nhanh_business_id', 0),
        #         "accessToken": nhanh_config.get('nhanh_connector.nhanh_access_token', ''),
        #         "data": json.dumps(kwargs)
        #     }

        #     # Get all orders from previous day to today from Nhanh.vn
        #     print('----- brand_id', brand_id.id)
        #     try:
        #         res_server = requests.post(url, data=data)
        #         res = res_server.json()
        #         print(res)
        #     except Exception as ex:
        #         _logger.info(f'Get orders from NhanhVn error {ex}')
        #         continue
        #     if res['code'] == 0:
        #         _logger.info(f'Get order error {res["messages"]}')
        #         continue

            
        #     print('------------', brand_id.id)
        #     list_customers = constant.get_customers_from_nhanh(self, brand_id=brand_id.id)

        #     res_data = res.get('data')
        #     nhanh_orders = res['data']['orders']
            
        #     # for page in range(2, res_data.get('totalRecords') + 1):
        #     #     kwargs['page'] = page
        #     #     data["data"] = json.dumps(kwargs)
        #     #     try:
        #     #         res_page_server = requests.post(url, data=data)
        #     #         res_page_data = res_page_server.json()
        #     #         nhanh_orders.update(res_page_data['data']['orders'])
        #     #     except Exception as e:
        #     #         _logger.info(str(e))
        #     #         pass
                
        #     for item in odoo_order_ids:
        #         if nhanh_orders.get(item):
        #         # if item in nhanh_orders:
        #             nhanh_orders.pop(item)

        #     # _logger.info(nhanh_orders)
        #     res_partner = partner_model.sudo().search([
        #         '|', ('mobile','!=',False),
        #         ('phone','!=',False)
        #     ])
        #     for k, v in nhanh_orders.items():
        #         try:
        #             name_customer = False
        #             if not v['customerMobile']:
        #                 continue

        #             partner = res_partner.filtered(
        #                 lambda r: r.customer_nhanh_id == v['customerId'] or r.mobile == v['customerMobile']
        #                 or r.phone == v['customerMobile']
        #             )
        #             if partner:
        #                 name_customer = v['customerName']
        #             if not partner:
        #                 customer = list_customers.get(str(v['customerId']))

        #                 partner_value = {
        #                     'phone': v['customerMobile'],
        #                     'mobile': v['customerMobile'],
        #                     'name': v['customerName'],
        #                     'email': v['customerEmail'],
        #                     'contact_address_complete': v['customerAddress'],
        #                     'customer_nhanh_id': v['customerId'],
        #                     'group_id': partner_group_id.id if partner_group_id else None
        #                 }
        #                 if customer:
        #                     gender = ""
        #                     if customer["gender"]:
        #                         gender = constant.mapping_gender_nhanh.get(customer["gender"])

        #                     partner_value.update({
        #                         'gender': gender,
        #                         'birthday': customer["birthday"],
        #                         'vat': customer["taxCode"],
        #                     })

        #                 partner = partner_model.sudo().create(partner_value)
        #             order_line = []
                    
        #             location_id = location_ids.filtered(lambda r: r.nhanh_id == int(v['depotId']))

        #             for item in v['products']:
        #                 product = self.search_product(('nhanh_id', '=', item.get('productId')))
        #                 if not product and item.get('productBarcode'):
        #                     product = self.search_product(('barcode', '=', item.get('productBarcode')))
        #                 if not product and item.get('productCode'):
        #                     product = self.search_product(('barcode', '=', item.get('productCode')))
        #                 if not product:
        #                     product = self.env['product.template'].create({
        #                         'detailed_type': 'asset',
        #                         'nhanh_id': item.get('productId'),
        #                         'check_data_odoo': False,
        #                         'name': item.get('productName'),
        #                         'barcode': item.get('productBarcode'),
        #                         # 'code_product': item.get('productCode'),
        #                         'list_price': item.get('price'),
        #                         'uom_id': uom,
        #                         'weight': item.get('shippingWeight', 0),
        #                         'responsible_id': None
        #                     })
        #                 product_product = self.env['product.product'].search([('product_tmpl_id', '=', product.id)],
        #                                                                      limit=1)
        #                 order_line.append((
        #                     0, 0,
        #                     {'product_template_id': product.id, 'product_id': product_product.id, 'name': product.name,
        #                      'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
        #                      'product_uom': product.uom_id.id if product.uom_id else uom,
        #                      'customer_lead': 0, 'sequence': 10, 'is_downpayment': False,
        #                      'x_location_id': location_id.id if location_id else None,
        #                      'discount': float(item.get('discount')) / float(item.get('price')) * 100 if item.get(
        #                          'discount') else 0,
        #                      'x_cart_discount_fixed_price': float(item.get('discount')) * float(
        #                          item.get('quantity')) if item.get('discount') else 0}))
        #             # Add orders  to odoo
        #             _logger.info(v)
        #             status = 'draft'
        #             if v['statusCode'] == 'confirmed':
        #                 status = 'draft'
        #             elif v['statusCode'] in ['Packing', 'Pickup']:
        #                 status = 'sale'
        #             elif v['statusCode'] in ['Shipping', 'Returning']:
        #                 status = 'sale'
        #             elif v['statusCode'] == 'success':
        #                 status = 'done'
        #             elif v['statusCode'] == 'canceled':
        #                 status = 'cancel'

        #             # nhân viên kinh doanh
        #             user_id = self.env['res.users'].search([('partner_id.name', '=', v['saleName'])], limit=1)
        #             # đội ngũ bán hàng
        #             team_id = self.env['crm.team'].search([('name', '=', v['trafficSourceName'])], limit=1)
        #             default_company_id = self.env['res.company'].sudo().search([('code', '=', '1300')], limit=1)
        #             # warehouse_id = self.env['stock.warehouse'].search([('nhanh_id', '=', int(v['depotId']))], limit=1)
        #             # if not warehouse_id:
        #             #     warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', default_company_id.id)],
        #             #                                                       limit=1)
        #             # delivery carrier
        #             delivery_carrier_id = self.env['delivery.carrier'].sudo().search(
        #                 [('nhanh_id', '=', v['carrierId'])], limit=1)
        #             if not delivery_carrier_id:
        #                 delivery_carrier_id = self.env['delivery.carrier'].sudo().create({
        #                     'nhanh_id': v['carrierId'],
        #                     'name': v['carrierName'],
        #                     'code': v['carrierCode'],
        #                     'service_name': v['carrierServiceName']
        #                 })
        #             value = {
        #                 'nhanh_id': v['id'],
        #                 'nhanh_order_status': v['statusCode'].lower(),
        #                 'partner_id': nhanh_partner.id,
        #                 'order_partner_id': partner.id,
        #                 'nhanh_shipping_fee': v['shipFee'],
        #                 'nhanh_customer_shipping_fee': v['customerShipFee'],
        #                 'nhanh_sale_channel_id': v['saleChannel'],
        #                 'source_record': True,
        #                 'state': status,
        #                 'code_coupon': v['couponCode'],
        #                 'name_customer': name_customer,
        #                 'note': v['privateDescription'],
        #                 'note_customer': v['description'],
        #                 'x_sale_chanel': 'online',
        #                 # 'carrier_name': v['carrierName'],
        #                 'user_id': user_id.id if user_id else None,
        #                 'team_id': team_id.id if team_id else None,
        #                 'company_id': default_company_id.id if default_company_id else None,
        #                 'warehouse_id': location_id.warehouse_id.id if location_id and location_id.warehouse_id else None,
        #                 'delivery_carrier_id': delivery_carrier_id.id,
        #                 'order_line': order_line
        #             }
        #             # đổi hàng
        #             if v.get('returnFromOrderId', 0):
        #                 origin_order_id = self.env['sale.order'].sudo().search(
        #                     [('nhanh_id', '=', v.get('returnFromOrderId', 0))], limit=1)
        #                 value.update({
        #                     'x_is_return': True,
        #                     'x_origin': origin_order_id.id if origin_order_id else None,
        #                     'nhanh_origin_id': v.get('returnFromOrderId', 0)
        #                 })
        #             order_model.sudo().create(value)
        #         except Exception as e:
        #             _logger.info(str(e))
        #             pass
        #     break

        # _logger.info("----------------Sync orders from NhanhVn done--------------------")

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



    def create_stock_picking_so_from_nhanh_with_return_so(self):
        so_id = self.x_origin
        picking_ids = so_id.picking_ids.filtered(lambda p: p.state == 'done' and p.picking_type_id.sequence_code != 'PICK')
        for picking_id in picking_ids:
            ctx = {
                'active_id':picking_id.id, 
                'active_ids':picking_id.ids,
                'active_model':'stock.picking',
                'picking_id': picking_id.id,
                'so_return': self.id,
                'allowed_company_ids': [picking_id.company_id.id],
                'validate_analytic': True,
                'x_return': True,
            }

            stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(ctx))
            return_wiz = stock_return_picking_form.save()
            stock_return_picking_action = return_wiz.with_context(ctx)._create_returns()
        picking_return = self.picking_ids
        if picking_return:
            for pr in picking_return:
                pr.with_context(super=True).confirm_from_so(True)
        self.state = 'sale'

    def create_picking_return(self, nhanh_status=None):
        so_id = self
        pick_picking_ids = so_id.picking_ids.filtered(
            lambda p: p.state == 'done' and p.picking_type_id.sequence_code == 'PICK')
        pick_picking_not_done_ids = so_id.picking_ids.filtered(
            lambda p: p.state != 'done' and p.picking_type_id.sequence_code == 'PICK')
        out_picking_ids = so_id.picking_ids.filtered(lambda p: p.picking_type_id.sequence_code != 'PICK')

        for opicking in pick_picking_not_done_ids:
            opicking.action_cancel()
        for opicking in out_picking_ids:
            opicking.action_cancel()

        if nhanh_status and nhanh_status == 'Returned':
            for picking_id in pick_picking_ids:
                ctx = {
                    'active_id': picking_id.id,
                    'active_ids': picking_id.ids,
                    'active_model': 'stock.picking',
                    'picking_id': picking_id.id,
                    'so_return': self.id,
                    'allowed_company_ids': [picking_id.company_id.id],
                    'validate_analytic': True,
                    'x_return': True
                }

                stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(ctx))
                return_wiz = stock_return_picking_form.save()
                return_wiz.location_id = picking_id.location_id
                stock_return_picking_action = return_wiz.with_context(ctx)._create_returns()
                picking_return_created = self.env['stock.picking'].browse(stock_return_picking_action[0])
                picking_return_created.with_context(super=True).confirm_from_so(True)

