from odoo import http
from odoo.http import request, Response
import json
import logging
from odoo import api, fields, models, _
from odoo.addons.nhanh_connector.models import constant

event_type_mapping = {
    'orderAdd': 'order_add',
    'orderUpdate': 'order_update',
    'orderDelete': 'order_delete',
    'webhooksEnabled': 'webhook_enabled'
}

_logger = logging.getLogger(__name__)


class MainController(http.Controller):

    @http.route('/nhanh/webhook/handler', type='http', auth='public', methods=['POST'], csrf=False)
    def nhanh_webhook_handler(self, **post):
        value = json.loads(request.httprequest.data)
        event_type = value.get('event')
        webhook_value_id = None
        if event_type in ['orderAdd', 'orderUpdate', 'orderDelete']:
            webhook_value_id = request.env['nhanh.webhook.value'].sudo().create({
                'event_type': event_type_mapping.get(event_type, ''),
                'event_value': value,
            })
        try:
            data = value.get('data')
            result_requests = self.handle_order(event_type, data, webhook_value_id)
            if result_requests.get('code') != 200 and webhook_value_id:
                webhook_value_id.update({
                    'error': result_requests.get('message')
                })
            elif result_requests.get('code') == 200 and webhook_value_id:
                webhook_value_id.update({
                    'state': 'done'
                })
        except Exception as ex:
            _logger.info(f'Webhook to system odoo false{ex}')
            if webhook_value_id:
                webhook_value_id.update({
                    'error': ex
                })
            result_requests = self.result_request(404, 0, _('Webhook to system odoo false'))
        return request.make_response(json.dumps(result_requests),
                                     headers={'Content-Type': 'application/json'})

    def handle_order(self, event_type, data, webhook_value_id=None):
        order_id = data.get('orderId') if event_type != 'orderDelete' else False
        order = self.sale_order_model().sudo().search([('nhanh_id', '=', order_id)],
                                                      limit=1) if event_type != 'orderDelete' else False
        if event_type == 'orderAdd':
            order = constant.get_order_from_nhanh_id(request, order_id)
            if not order:
                return self.result_request(404, 1, _('Không lấy được thông tin đơn hàng từ Nhanh'))
            name_customer = False
            # Add customer if not existed
            nhanh_partner = self.partner_model().sudo().search(
                [('code_current_customers', '=', 'code_current_customers_nhanhvn')], limit=1)
            if not nhanh_partner:
                nhanh_partner = self.partner_model().sudo().create({
                    'code_current_customers': 'code_current_customers_nhanhvn',
                    'name': 'Nhanh.Vn',
                    'customer_rank': 1
                })
            partner = self.partner_model().sudo().search(
                ['|', ('mobile', '=', data['customerMobile']), ('phone', '=', data['customerMobile'])], limit=1)
            if partner:
                name_customer = data['customerName']
            if not partner:
                partner_value = {
                    'phone': data['customerMobile'],
                    'mobile': data['customerMobile'],
                    'name': data['customerName'],
                    'email': data['customerEmail'],
                    'contact_address_complete': data['customerAddress'],
                    'customer_nhanh_id': data['customerId'],
                }
                partner = self.partner_model().sudo().create(partner_value)
            order_line = []
            location_id = request.env['stock.location'].search([('nhanh_id', '=', int(order['depotId']))], limit=1)
            for item in data['products']:
                product = self.product_template_model().sudo().search([('nhanh_id', '=', item.get('id'))], limit=1)
                product_product = self.product_product_model().sudo().search([('product_tmpl_id', '=', product.id)],
                                                                             limit=1)
                order_line.append((
                    0, 0, {'product_template_id': product.id, 'product_id': product_product.id, 'name': product.name,
                           'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
                           'product_uom': product.uom_id.id if product.uom_id else self.uom_unit(),
                           'customer_lead': 0, 'sequence': 10, 'is_downpayment': False, 'x_location_id': location_id.id,
                           'discount': float(item.get('discount')) / float(item.get('price')) * 100 if item.get(
                               'discount') else 0,
                           'x_cart_discount_fixed_price': float(item.get('discount')) * float(
                               item.get('quantity')) if item.get('discount') else 0}))

            status = 'draft'
            if data['status'] == 'confirmed':
                status = 'draft'
            elif data['status'] in ['Packing', 'Pickup']:
                status = 'sale'
            elif data['status'] in ['Shipping', 'Returning']:
                status = 'sale'
            elif data['status'] == 'success':
                status = 'done'
            elif data['status'] == 'canceled':
                status = 'cancel'

            # nhân viên kinh doanh
            user_id = request.env['res.users'].search([('partner_id.name', '=', order['saleName'])], limit=1)
            # đội ngũ bán hàng
            team_id = request.env['crm.team'].search([('name', '=', order['trafficSourceName'])], limit=1)
            default_company_id = request.env['res.company'].sudo().search([('code', '=', '1300')], limit=1)
            # warehouse_id = request.env['stock.warehouse'].search([('nhanh_id', '=', int(data['depotId']))], limit=1)
            # if not warehouse_id:
            #     warehouse_id = request.env['stock.warehouse'].search([('company_id', '=', default_company_id.id)], limit=1)
            value = {
                'nhanh_id': data['orderId'],
                'nhanh_status': data['status'],
                'partner_id': nhanh_partner.id,
                'order_partner_id': partner.id,
                'nhanh_shipping_fee': data['shipFee'],
                'source_record': True,
                'code_coupon': data['couponCode'],
                'state': status,
                'nhanh_order_status': data['status'].lower(),
                'name_customer': name_customer,
                'note': order['privateDescription'],
                'note_customer': data['description'],
                'x_sale_chanel': 'online',
                'carrier_name': order['carrierName'],
                'user_id': user_id.id if user_id else None,
                'team_id': team_id.id if team_id else None,
                'company_id': default_company_id.id if default_company_id else None,
                'warehouse_id': location_id.warehouse_id.id if location_id and location_id.warehouse_id else None,
                'order_line': order_line
            }
            # đổi trả hàng
            if order.get('returnFromOrderId', 0):
                origin_order_id = request.env['sale.order'].sudo().search(
                    [('nhanh_id', '=', order.get('returnFromOrderId', 0))], limit=1)
                value.update({
                    'x_is_return': True,
                    'x_origin': origin_order_id.id if origin_order_id else None,
                    'nhanh_origin_id': order.get('returnFromOrderId', 0)
                })
            self.sale_order_model().sudo().create(value)
            return self.result_request(200, 0, _('Create sale order success'))
        elif event_type == 'orderUpdate':
            if data.get('status'):
                status = 'draft'
                if data['status'] == 'confirmed':
                    status = 'draft'
                elif data['status'] in ['Packing', 'Pickup']:
                    status = 'sale'
                elif data['status'] in ['Shipping', 'Returning']:
                    status = 'sale'
                elif data['status'] == 'success':
                    status = 'done'
                elif data['status'] == 'canceled':
                    status = 'cancel'
                order.sudo().write({
                    'state': status,
                    'nhanh_order_status': data['status'].lower(),
                })
                if status == 'cancel' and order.picking_ids and 'done' in order.picking_ids.mapped('state'):
                    order.picking_ids.unlink()
                return self.result_request(200, 0, _('Update sale order success'))
            else:
                return self.result_request(404, 1, _('Update sale order false'))
        elif event_type == 'orderDelete':
            for item in data:
                order_ids = self.sale_order_model().sudo().search([('nhanh_id', '=', int(item))]).sudo()
                order_ids.write({
                    'state': 'cancel',
                    'nhanh_order_status': 'canceled',
                })
                for order_id in order_ids:
                    if not order_id.picking_ids:
                        continue
                    if 'done' in order_id.picking_ids.mapped('state'):
                        continue
                    order_id.picking_ids.unlink()
            return self.result_request(200, 0, _('Delete sale order success'))

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
