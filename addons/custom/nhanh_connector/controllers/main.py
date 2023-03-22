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
            'productAdd': self.handle_product,
            'productUpdate': self.handle_product,
            'productDelete': self.handle_product,
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
            if data.get('status') == 'confirmed':
                status = 'sale'
            elif data.get('status') == 'success':
                status = 'done'
            elif data.get('status') == 'canceled':
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

    def handle_product(self, event_type, data):
        self.data_product_category_nhanh()
        product_id = data.get('productId') if event_type != 'productDelete' else False
        product_template = self.product_template_model().sudo().search([('nhanh_id', '=', product_id)], limit=1) if event_type != 'productDelete' else False
        category = request.env['product.category'].sudo().search([('nhanh_product_category_id', '=', data.get('categoryId'))], limit=1)
        if event_type == 'productAdd':
            data_product = {
                'nhanh_id': data.get('productId'),
                'check_data_odoo': False,
                'name': data.get('name'),
                'code_product': data.get('code'),
                'uom_id': self.uom_unit(),
                'detailed_type': 'asset',
                'create_date': data.get('createdDateTime'),
                'width_product': float(data.get('width')),
                'height_product': float(data.get('height')),
            }
            if category:
                data_product.update({
                    'categ_id': category.id
                })
            product = self.product_template_model().sudo().create(data_product)
            return self.result_request(200, 0, _('Create product success'))
        elif event_type == 'productUpdate':
            product_template.sudo().write({
                    'name': data.get('name'),
                    'categ_id': category.id if category else False
                })
            return self.result_request(200, 0, _('Update product success'))
        elif event_type == 'productDelete':
            for item in data:
                product_template = self.product_template_model().sudo().search([('nhanh_id', '=', int(item))]).sudo().unlink()
            return self.result_request(200, 0, _('Delete product success'))


    #Hàm tạo category
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
            product_category = request.env['product.category'].sudo().search([('code_category', '=', str(category['code']))])
            if not product_category:
                new_category = request.env['product.category'].sudo().create({
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