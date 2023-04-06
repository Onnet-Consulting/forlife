import requests

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


def get_params(self):
    nhanh_configs = get_nhanh_configs(self)
    query_params = {
        'version': '2.0',
         'appId': f"{nhanh_configs['nhanh_connector.nhanh_app_id']}",
        'businessId': f"{nhanh_configs['nhanh_connector.nhanh_business_id']}",
        'accessToken': f"{nhanh_configs['nhanh_connector.nhanh_access_token']}",
    }
    return query_params


def base_url():
    return 'https://open.nhanh.vn/api'


def get_post_status(self, status, rec):
    nhanh_configs = get_nhanh_configs(self)
    data = '{"orderId": "' + str(rec.nhanh_id) + '", "status": "' + status + '"}'
    url = f"{base_url()}/order/update?version=2.0&appId={nhanh_configs['nhanh_connector.nhanh_app_id']}" \
          f"&businessId={nhanh_configs['nhanh_connector.nhanh_business_id']}&accessToken={nhanh_configs['nhanh_connector.nhanh_access_token']}" \
          f"&data={data}"
    res_server = requests.post(url)
    return res_server

def get_nhanh_configs(self):
    '''
    Get nhanh config from ir_config_parameter table
    '''
    params = self.env['ir.config_parameter'].sudo().search([('key', 'ilike', 'nhanh_connector.nhanh_')]).read(['key', 'value'])
    nhanh_configs = {}
    for param in params:
        nhanh_configs[param['key']] = param['value']
    return nhanh_configs