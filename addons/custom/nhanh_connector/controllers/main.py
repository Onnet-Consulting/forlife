from odoo import http
from odoo.http import request, Response
import json
import logging
from odoo import api, fields, models, _
from odoo.addons.nhanh_connector.models import constant
import datetime
import requests

_logger = logging.getLogger(__name__)

class MainController(http.Controller):
    def __init__(self):
        self.event_handlers = {
            'orderAdd': self.handle_order,
            'orderUpdate': self.handle_order,
            'orderDelete': self.handle_order,
            'webhooksEnabled': self.webhook_enable,
        }

    @http.route('/nhanh/webhook/handler', type='http', auth='public', methods=['POST'], csrf=False)
    def nhanh_webhook_handler(self, **post):
        value = json.loads(request.httprequest.data)
        event_type = value.get('event')
        handler = self.event_handlers.get(event_type)
        result_requests = self.result_request(200, 0, _('Webhook to system odoo'))
        try:
            if handler:
                data = value.get('data')
                result_requests = handler(event_type, data)

            else:
                result_requests = self.result_requests(404, 0, _('Webhook to system odoo false'))
        except Exception as ex:
            _logger.info(f'Webhook to system odoo false{ex}')
            result_requests = self.result_request(404, 0, _('Webhook to system odoo false'))
        return request.make_response(json.dumps(result_requests),
                                  headers={'Content-Type': 'application/json'})

    def handle_order(self, event_type, data):
        order_id = data.get('orderId') if event_type != 'orderDelete' else False
        order = self.sale_order_model().sudo().search([('nhanh_id', '=', order_id)], limit=1) if event_type != 'orderDelete' else False
        if event_type == 'orderAdd':
            partner = self.partner_model().sudo().search([('code_current_customers', '=', 'code_current_customers_nhanhvn')], limit=1)
            if not partner:
                partner_value = {
                    'code_current_customers': 'code_current_customers_nhanhvn',
                    'name': 'Current customers Nhanh.Vn',
                }
                partner = self.partner_model().sudo().create(partner_value)
            order_line = []
            for item in data['products']:
                product = self.product_template_model().sudo().search([('nhanh_id', '=', item.get('id'))], limit=1)
                product_product = self.product_product_model().sudo().search([('product_tmpl_id', '=', product.id)], limit=1)
                order_line.append((
                    0, 0, {'product_template_id': product.id, 'product_id': product_product.id, 'name': product.name,
                           'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
                           'product_uom': product.uom_id.id if product.uom_id else self.uom_unit(),
                           'customer_lead': 0, 'sequence': 10, 'is_downpayment': False, 'discount': item.get('discount')}))

            status = 'draft'
            if data['status'] == 'confirmed':
                status = 'draft'
            elif data['status'] in ('packing', 'pickup'):
                status = 'sale'
            elif data['status'] in ('shipping', 'returning'):
                status = 'sale'
            elif data['status'] == 'success':
                status = 'done'
            elif data['status'] == 'canceled':
                status = 'cancel'
            value = {
                'nhanh_id': data['orderId'],
                'nhanh_status': data['status'],
                'partner_id': partner.id,
                'nhanh_shipping_fee': data['shipFee'],
                'source_record': True,
                'code_coupon': data['couponCode'],
                'state': status,
                'name_customer': data['customerName'],
                'order_line': order_line
            }
            self.sale_order_model().sudo().create(value)
            return self.result_request(200, 0, _('Create sale order success'))
        elif event_type == 'orderUpdate':
            if data.get('status'):
                status = 'draft'
                if data.get('status') == 'Confirmed':
                    status = 'sale'
                elif data.get('status') == 'Success':
                    status = 'done'
                elif data.get('status') == 'Canceled':
                    status = 'cancel'
                order.sudo().write({
                    'state': status
                })
                return self.result_request(200, 0, _('Update sale order success'))
            else:
                return self.result_request(404, 1, _('Update sale order false'))
        elif event_type == 'orderDelete':
            for item in data:
                order_unlink = self.sale_order_model().sudo().search([('nhanh_id', '=', int(item))]).sudo().write({
                    'state': 'cancel'
                })
            return self.result_request(200, 0, _('Delete sale order success'))

    def get_nhanh_configs(self):
        '''
        Get nhanh config from ir_config_parameter table
        '''
        params = request.env['ir.config_parameter'].sudo().search([('key', 'ilike', 'nhanh_connector.nhanh_')]).read(['key', 'value'])
        nhanh_configs = {}
        for param in params:
            nhanh_configs[param['key']] = param['value']
        return nhanh_configs

    def get_link_nhanh(self, category, type_get, data):
        nhanh_configs = self.get_nhanh_configs()
        if 'nhanh_connector.nhanh_app_id' not in nhanh_configs or 'nhanh_connector.nhanh_business_id' not in nhanh_configs \
                or 'nhanh_connector.nhanh_access_token' not in nhanh_configs:
            _logger.info(f'Nhanh configuration does not set')
            return False
        url = f"{constant.base_url()}/{category}/{type_get}?version={self.get_params()['version']}&appId={self.get_params()['appId']}" \
              f"&businessId={self.get_params()['businessId']}&accessToken={self.get_params()['accessToken']}" \
              f"&data={data}"
        return url

    def get_params(self):
        nhanh_configs = self.get_nhanh_configs()
        query_params = {
            'version': '2.0',
            'appId': f"{nhanh_configs['nhanh_connector.nhanh_app_id']}",
            'businessId': f"{nhanh_configs['nhanh_connector.nhanh_business_id']}",
            'accessToken': f"{nhanh_configs['nhanh_connector.nhanh_access_token']}",
        }
        return query_params
    # End Create Category

    def webhook_enable(self, event_type, data):
        return self.result_request(200, 0, _('Webhook enable success'))

    def partner_model(self):
        return request.env['res.partner']

    def sale_order_model(self):
        return request.env['sale.order']

    def product_template_model(self):
        return request.env['product.template']

    def product_product_model(self):
        return request.env['product.product']

    def uom_unit(self):
        return request.env.ref('uom.product_uom_unit').id

    def result_request(self, code, status, message):
        result = {
            'code': code,
            'status': status,
            'message': message
        }
        return result