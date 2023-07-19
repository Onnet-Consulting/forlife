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

    def get_brand(self):
        return self.cls.env['res.brand'].sudo().search([('code', '=', self.cls.brand_code)], limit=1)

    def get_partner_group(self):
        return self.cls.env['res.partner.group'].sudo().search([('code', '=', 'C')], limit=1)

    def get_res_partner(self, partner_group_id, order):
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




