import requests
import logging
import json

_logger = logging.getLogger(__name__)

class NhanhClient:
    def __init__(self, request, constant):
        self.cls = request
        self.constant = constant

    def get_sale_order(self, order_id):
        return self.cls.env['sale.order'].sudo().search([('nhanh_id', '=', order_id)], limit=1)

    def get_company(self):
        return self.cls.env['res.company'].sudo().search([('code', '=', '1300')], limit=1)

    def get_location_by_company(self, default_company_id, nhanh_id):
        return self.cls.env['stock.location'].sudo().search([
            ('nhanh_id', '=', nhanh_id),
            ('company_id', '=', default_company_id.id)
        ],limit=1)


    def get_nhanh_partner(self):
        nhanh_partner = self.cls.env['res.partner'].sudo().search([
            ('code_current_customers', '=', 'code_current_customers_nhanhvn')
        ], limit=1)
        if not nhanh_partner:
            nhanh_partner = self.cls.env['res.partner'].sudo().create({
                'code_current_customers': 'code_current_customers_nhanhvn',
                'name': 'Nhanh.Vn',
                'customer_rank': 1
            })
        return nhanh_partner

    def get_sale_channel(self, order):
        sale_channel = self.cls.env['sale.channel'].sudo().search([('nhanh_id', '=', int(order["saleChannel"]))], limit=1)
        return sale_channel


    def get_brand(self):
        config = self.cls.env['nhanh.brand.config'].sudo().search([('nhanh_business_id', '=', self.cls.business_id)], limit=1)
        # config = self.cls.env['nhanh.brand.config'].sudo().search([('id', '=', 6)], limit=1)
        return config.brand_id

    def get_partner_group(self):
        return self.cls.env['res.partner.group'].sudo().search([('code', '=', 'C')], limit=1)

    def get_res_partner(self, partner_group_id, order):
        # sale channel
        sale_channel = self.get_sale_channel(order)
        if sale_channel and sale_channel.is_tmdt:
            return sale_channel.partner_id

        return self.cls.env['res.partner'].sudo().search([
            '|', 
            ('mobile', '=', order['customerMobile']), 
            ('phone', '=', order['customerMobile']),
            ('group_id', '=', partner_group_id.id)
        ], limit=1)


    def create_res_partner(self, order, brand_id, partner_group_id, customer):
        retail_type_ids = self.cls.env['res.partner.retail'].sudo().search([
            ('brand_id', '=', brand_id.id), 
            ('code', 'in', ('3', '6'))
        ]).ids
        partner_value = {
            'phone': order['customerMobile'],
            'mobile': order['customerMobile'],
            'name': order['customerName'],
            'email': order['customerEmail'],
            'street': order['customerAddress'],
            'contact_address_complete': order['customerAddress'],
            'customer_nhanh_id': order['customerId'],
            'retail_type_ids': [(6, 0, retail_type_ids)],
            'group_id': partner_group_id.id if partner_group_id else None
        }
        if customer:
            gender = ""
            if customer["gender"]:
                gender = self.constant.mapping_gender_nhanh.get(customer["gender"])

            partner_value.update({
                'gender': gender,
                'birthday': customer["birthday"],
                'vat': customer["taxCode"],
            })
        return self.cls.env['res.partner'].sudo().create(partner_value)

    def get_order_from_nhanh_id(self, order_id, brand_id):
        nhanh_configs = self.constant.get_nhanh_configs(self.cls)
        nhanh_config = nhanh_configs.get(brand_id.id, {})
        if not nhanh_config:
            msg = f"The configuration information does not exists for {brand_id.code} this brand. Please log into the system and add information"
            _logger.info(msg)
            raise ValueError(msg)
        
        # Won't run if exist at least one empty param
        if 'nhanh_connector.nhanh_app_id' not in nhanh_config or 'nhanh_connector.nhanh_business_id' not in nhanh_config \
                or 'nhanh_connector.nhanh_access_token' not in nhanh_config:
            msg = f'Nhanh configuration does not set'
            _logger.info(f'Nhanh configuration does not set')
            raise ValueError(msg)

        url = f"{self.constant.NHANH_BASE_URL}/order/index"
        data = {
            "version": 2.0,
            "appId": '%s' % nhanh_config.get('nhanh_connector.nhanh_app_id', 0),
            "businessId": '%s' % nhanh_config.get('nhanh_connector.nhanh_business_id', 0),
            "accessToken": nhanh_config.get('nhanh_connector.nhanh_access_token', ''),
            "data": '{"id": %s}' % (order_id)
        }
        try:
            res_server = requests.post(url, data=data)
            res = res_server.json()
        except Exception as ex:
            msg = f'Get orders from NhanhVn error {ex}'
            _logger.info(msg)
            raise ValueError(msg)

        if res['code'] == 0:
            msg = f'Get order error {res["messages"]}'
            _logger.info(msg)
            raise ValueError(msg)

        if not res['data']['orders'].get(str(order_id)):
            msg = f"This {str(order_id)} order does not exists"
            raise ValueError(msg)

        return res['data']['orders'].get(str(order_id))


    def check_customer_exists_store_first_order(self, partner):
        res = self.cls.env['store.first.order'].sudo().search([('customer_id', '=', partner.id)])
        if res:
            return True
        return False

    def create_store_first_order_for_customer(self, partner, nhanh_id):
        locations = self.cls.env['stock.location'].sudo().search([
            ('nhanh_id', '=', nhanh_id)
        ]).mapped("warehouse_id")

        store = self.cls.env['store'].sudo().search([
            ('warehouse_id', 'in', locations.ids),
        ],limit=1)
        if store:
            vals_list = {
                'customer_id': partner.id,
                'brand_id': store.brand_id.id,
                'store_id': store.id,
            }

            self.cls.env['store.first.order'].sudo().create([vals_list])

    def get_order_line(self, order, brand_id, location_id, is_create=False):
        order_line = []
        for item in order['products']:
            product_id = self.cls.env['product.product'].sudo().search([
                ('nhanh_id', '=', item.get('productId'))
            ],limit=1)
            # product_id = self.cls.env['product.product'].sudo().search(['|',
            #     ('nhanh_id', '=', item.get('productId')),
            #     ('barcode', '=', item.get('productBarcode'))
            # ],limit=1)

            if not product_id:
                raise ValueError('Không có sản phẩm có id nhanh là %s' % item.get('productId'))

            # if not product_id and not is_create:
            #     raise ValueError('Không có sản phẩm có id nhanh là %s' % item.get('productId'))
            # if not product_id and is_create: 
            #     uom = self.cls.env.ref('uom.product_uom_unit').id
            #     product = self.cls.env['product.template'].sudo().create({
            #         'detailed_type': 'asset',
            #         'nhanh_id': item.get('productId'),
            #         'check_data_odoo': False,
            #         'name': item.get('productName'),
            #         'barcode': item.get('productBarcode'),
            #         'list_price': item.get('price'),
            #         'uom_id': uom,
            #         'weight': float(item.get('weight', 0)/1000),
            #         'responsible_id': None
            #     })
            #     product_id = self.cls.env['product.product'].sudo().search([
            #         ('product_tmpl_id', '=', product.id)
            #     ], limit=1)

            # product_id.product_tmpl_id.write({
            #     'brand_id': brand_id.id,
            #     'nhanh_id': item.get('productId'),
            #     'check_data_odoo': True,
            # })

            order_line.append((
                0, 0, {
                    'product_template_id': product_id.product_tmpl_id.id, 
                    'product_id': product_id.id,
                    'name': product_id.name,
                    'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
                    'product_uom': product_id.uom_id.id if product_id.uom_id else self.uom_unit(),
                    'customer_lead': 0, 'sequence': 10, 'is_downpayment': False,
                    'x_location_id': location_id.id,
                    # 'discount': float(item.get('discount')) / float(item.get('price')) * 100 if item.get(
                       #     'discount') else 0,
                    'x_cart_discount_fixed_price': float(item.get('discount')) * float(
                           item.get('quantity')) if item.get('discount') else 0}
            ))
        return order_line

    def get_sales_staff(self, order):
        
        return self.cls.env['res.users'].sudo().search([('partner_id.name', '=', order['saleName'])], limit=1)

    def get_sales_team(self, order):
        return self.cls.env['crm.team'].sudo().search([('name', '=', order['trafficSourceName'])], limit=1)

    def get_and_create_delivery_carrier(self, order):
        delivery_carrier_id = self.cls.env['delivery.carrier'].sudo().search(
            [('nhanh_id', '=', order['carrierId'])], limit=1)
        if not delivery_carrier_id:
            delivery_carrier_id = self.cls.env['delivery.carrier'].sudo().create({
                'nhanh_id': order['carrierId'],
                'name': order['carrierName'],
                'code': order['carrierCode'],
                'service_name': order['serviceName']
            })
        return delivery_carrier_id

    def get_and_create_utm_source(self, order):
        if not order['trafficSourceId']:
            return None
        utm_source_id = self.cls.env['utm.source'].sudo().search([('x_nhanh_id', '=', order['trafficSourceId'])])
        if not utm_source_id:
            utm_source_id = self.cls.env['utm.source'].sudo().create({
                'x_nhanh_id': order['trafficSourceId'],
                'name': order['trafficSourceName'],
            })
        return utm_source_id

    def get_order_data(self, order, nhanh_partner, partner, name_customer, default_company_id, location_id):
        # sales staff
        user_id = self.get_sales_staff(order)

        # sales team
        team_id = self.get_sales_team(order)
        
        
        delivery_carrier_id = self.get_and_create_delivery_carrier(order)

        # utm source
        utm_source_id = self.get_and_create_utm_source(order)

        # sale channel
        sale_channel = self.get_sale_channel(order)

        x_transfer_code = order['carrierCode']
        if sale_channel and sale_channel.is_tmdt:
            x_transfer_code = order['privateId']

        order_data = {
            'nhanh_id': order['id'],
            'partner_id': nhanh_partner.id,
            'order_partner_id': partner.id,
            'nhanh_shipping_fee': order['shipFee'],
            'nhanh_customer_shipping_fee': order['customerShipFee'],
            'source_record': True,
            'code_coupon': order['couponCode'],
            'state': 'draft',
            'nhanh_order_status': order['statusCode'].lower(),
            'name_customer': name_customer,
            'note': order["privateDescription"],
            'note_customer': order['description'],
            'x_sale_chanel': 'online',
            'user_id': user_id.id if user_id else None,
            'team_id': team_id.id if team_id else None,
            'company_id': default_company_id.id if default_company_id else None,
            'warehouse_id': location_id.warehouse_id.id if location_id and location_id.warehouse_id else None,
            'delivery_carrier_id': delivery_carrier_id.id,
            'nhanh_customer_phone': order['customerMobile'],
            'source_id': utm_source_id.id if utm_source_id else None,
            'x_location_id': location_id.id,
            'sale_channel_id': sale_channel.id if sale_channel else None,
            'x_transfer_code': x_transfer_code if x_transfer_code else '',
        }
        return order_data

    def order_paid_online(self, order):
        # Check the order is paid online or not
        private_description = order["privateDescription"]
        if private_description.find("#VC") != -1:
            x_voucher = order["moneyTransfer"]
            x = private_description.split("#VC")
            y = x[1].strip()
            z = y.split()
            x_code_voucher = z[0]
        else:
            x_voucher = 0
            x_code_voucher = ""
        return x_voucher, x_code_voucher


    def order_return_and_changed(self, order):
        private_description = order["privateDescription"]
        #X270941175 #N270941350
        return_changed = None
        if private_description.find("#X") != -1 and private_description.find("#N") != -1:
            x = private_description.split()
            return_changed = {
                "x_is_change": True,
            }
            for v in x:
                if v.find("#X") != -1 or v.find("#N") != -1:
                    y = v.strip()
                    if y.find("#X") != -1:
                        z = y.replace("#X", "")
                        origin_order_id = self.cls.env['sale.order'].sudo().search(
                            [('nhanh_id', '=', z)], limit=1)
                        return_changed['x_origin'] = origin_order_id.id if origin_order_id else None
                        return_changed['nhanh_origin_id'] = z

                    if y.find("#N") != -1:
                        z = y.replace("#N", "")
                        return_changed['nhanh_return_id'] = z
                else:
                    continue
        return return_changed

