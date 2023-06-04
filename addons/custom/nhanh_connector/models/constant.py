import requests
import json


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
        nhanh_configs[config_id.id] = {
            'nhanh_connector.nhanh_business_id': config_id.nhanh_business_id,
            'nhanh_connector.nhanh_app_id': config_id.nhanh_app_id,
            'nhanh_connector.nhanh_secret_key': config_id.nhanh_secret_key,
            'nhanh_connector.nhanh_access_code': config_id.nhanh_access_code,
            'nhanh_connector.nhanh_access_token': config_id.nhanh_access_token,
            'nhanh_connector.nhanh_access_token_expired': config_id.nhanh_access_token_expired,
            'nhanh_connector.nhanh_return_link': config_id.nhanh_return_link,
        }
    return nhanh_configs
