import requests
import logging

NHANH_BASE_URL = 'https://open.nhanh.vn/api'


def get_proxies():
    http_proxy = "http://10.207.210.3:3128"
    https_proxy = "https://10.207.210.3:3128"
    ftp_proxy = "ftp://10.207.210.3:3128"

    proxies = {
        "http": http_proxy,
        "https": https_proxy,
        "ftp": ftp_proxy
    }
    return proxies


_logger = logging.getLogger(__name__)


def get_params(self, brand_id=None):
    nhanh_configs = get_nhanh_configs(self, [brand_id]).get(brand_id)
    query_params = {
        'version': '2.0',
        'appId': nhanh_configs.get('nhanh_connector.nhanh_app_id', ''),
        'businessId': nhanh_configs.get('nhanh_connector.nhanh_business_id', ''),
        'accessToken': nhanh_configs.get('nhanh_connector.nhanh_access_token', ''),
    }
    return query_params


def base_url():
    return 'https://open.nhanh.vn/api'


# def get_post_status(self, status, rec):
#     data = {
#         'orderId': str(rec.nhanh_id),
#         'status': status
#     }
#     url = f"{base_url()}/order/update"
#     payload = get_params(self)
#     payload.update({
#         'data': json.dumps(data)
#     })
#     res_server = requests.post(url, data=payload)
#     return res_server


def get_nhanh_configs(self, brand_ids=None):
    '''
    Get nhanh config from nhanh_brand_config table
    '''
    nhanh_configs = {}
    if not brand_ids:
        brand_ids = self.env['res.brand'].sudo().search([]).ids
    config_ids = self.env['nhanh.brand.config'].sudo().search([('brand_id', 'in', brand_ids)])
    for config_id in config_ids:
        if nhanh_configs.get(config_id.id):
            continue
        nhanh_configs[config_id.brand_id.id] = {
            'nhanh_connector.nhanh_business_id': int(
                config_id.nhanh_business_id) if config_id.nhanh_business_id else '',
            'nhanh_connector.nhanh_app_id': int(config_id.nhanh_app_id) if config_id.nhanh_app_id else '',
            'nhanh_connector.nhanh_secret_key': config_id.nhanh_secret_key,
            'nhanh_connector.nhanh_access_code': config_id.nhanh_access_code,
            'nhanh_connector.nhanh_access_token': config_id.nhanh_access_token,
            'nhanh_connector.nhanh_access_token_expired': config_id.nhanh_access_token_expired,
            'nhanh_connector.nhanh_return_link': config_id.nhanh_return_link,
        }
    return nhanh_configs


def get_order_from_nhanh_id(self, order_id):
    order_information = None
    nhanh_configs = get_nhanh_configs(self)

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
            "data": '{"id": %s}' % (order_id)
        }
        try:
            res_server = requests.post(url, data=data)
            res = res_server.json()
        except Exception as ex:
            _logger.info(f'Get orders from NhanhVn error {ex}')
            continue
        if res['code'] == 0:
            _logger.info(f'Get order error {res["messages"]}')
            continue
        if not res['data']['orders'].get(str(order_id)):
            continue
        order_information = res['data']['orders'].get(str(order_id))
        break
    return order_information if order_information else res.get("messages", "")
