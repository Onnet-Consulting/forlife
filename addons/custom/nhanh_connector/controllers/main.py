from odoo import http
from odoo.http import request, Response
import json
import logging
from odoo import api, fields, models, _
from odoo.addons.nhanh_connector.models import constant
from .utils import NhanhClient

event_type_mapping = {
    'orderAdd': 'order_add',
    'orderUpdate': 'order_update',
    'orderDelete': 'order_delete',
    'webhooksEnabled': 'webhook_enabled'
}

NHANH_BASE_URL = 'https://open.nhanh.vn/api'

_logger = logging.getLogger(__name__)


class MainController(http.Controller):

    @http.route('/nhanh/webhook/handler/<string:brand_code>', type='http', auth='public', methods=['POST'], csrf=False)
    def nhanh_webhook_handler(self, brand_code, **post):
        request.brand_code = brand_code or None
        value = json.loads(request.httprequest.data)
        event_type = value.get('event')
        if event_type in ['orderUpdate']:
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
        n_client = NhanhClient(request, constant)
        order_id = data.get('orderId')
        brand_id = n_client.get_brand()
        try:
            order = n_client.get_order_from_nhanh_id(order_id, brand_id)
        except Exception as e:
            order = None

        if not order:
            return self.result_request(404, 1, _('Không lấy được thông tin đơn hàng từ Nhanh'))


        if event_type == 'orderUpdate':
            odoo_order = n_client.get_sale_order(order_id)
            is_create_wh_in = False
            if odoo_order and data['status'] in ['Returned']:
                odoo_order = None
                is_create_wh_in = True

            if not odoo_order:
                order_returned = order.get('returnFromOrderId', 0) and data['status'] in ['Returned', 'Success']
                order_returned_not_success = order.get('returnFromOrderId', 0) and data['status'] in ['Returned']
                if not is_create_wh_in:
                    if order_returned:
                        if order_returned_not_success:
                            return self.result_request(200, 0, _('Update sale order success'))
                    elif data['status'].lower() != "confirmed":
                        return self.result_request(404, 1, _('Order confirmation is required'))

                default_company_id = n_client.get_company()
                location_id = n_client.get_location_by_company(default_company_id, int(order['depotId']))

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
                    list_customers = constant.get_customers_from_nhanh(request, brand_id=brand_id.id, data={"mobile": order['customerMobile']})
                    customer = list_customers.get(str(order['customerId']))
                    partner = n_client.create_res_partner(order, brand_id, partner_group_id, customer)
                    if location_id and location_id.warehouse_id:
                        n_client.create_store_first_order_for_customer(
                            partner, int(order['depotId'])
                        )

                order_line = []
                
                for item in order['products']:
                    product_id = self.product_product_model().sudo().search([('nhanh_id', '=', item.get('productId'))],
                                                                            limit=1)
                    if not product_id:
                        raise ValueError('Không có sản phẩm có id nhanh là %s' % item.get('productId'))
                    product_id.product_tmpl_id.write({
                        'brand_id': brand_id.id
                    })
                    order_line.append((
                        0, 0, {'product_template_id': product_id.product_tmpl_id.id, 'product_id': product_id.id,
                               'name': product_id.name,
                               'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
                               'product_uom': product_id.uom_id.id if product_id.uom_id else self.uom_unit(),
                               'customer_lead': 0, 'sequence': 10, 'is_downpayment': False,
                               'x_location_id': location_id.id,
                               # 'discount': float(item.get('discount')) / float(item.get('price')) * 100 if item.get(
                               #     'discount') else 0,
                               'x_cart_discount_fixed_price': float(item.get('discount')) * float(
                                   item.get('quantity')) if item.get('discount') else 0}))

                # nhân viên kinh doanh
                user_id = request.env['res.users'].sudo().search([('partner_id.name', '=', order['saleName'])], limit=1)
                # đội ngũ bán hàng
                team_id = request.env['crm.team'].sudo().search([('name', '=', order['trafficSourceName'])], limit=1)
                
                # warehouse_id = request.env['stock.warehouse'].search([('nhanh_id', '=', int(data['depotId']))], limit=1)
                # if not warehouse_id:
                #     warehouse_id = request.env['stock.warehouse'].search([('company_id', '=', default_company_id.id)], limit=1)
                # delivery carrier
                delivery_carrier_id = request.env['delivery.carrier'].sudo().search(
                    [('nhanh_id', '=', order['carrierId'])], limit=1)
                if not delivery_carrier_id:
                    delivery_carrier_id = request.env['delivery.carrier'].sudo().create({
                        'nhanh_id': order['carrierId'],
                        'name': order['carrierName'],
                        'code': order['carrierCode'],
                        'service_name': order['serviceName']
                    })

                # nguồn đơn hàng
                utm_source_id = request.env['utm.source'].sudo().search([('x_nhanh_id', '=', order['trafficSourceId'])])
                if not utm_source_id:
                    utm_source_id = request.env['utm.source'].sudo().create({
                        'x_nhanh_id': order['trafficSourceId'],
                        'name': order['trafficSourceName'],
                    })
                value = {
                    'nhanh_id': order['id'],
                    'partner_id': nhanh_partner.id,
                    'order_partner_id': partner.id,
                    'nhanh_shipping_fee': order['shipFee'],
                    'source_record': True,
                    'code_coupon': order['couponCode'],
                    'state': 'draft',
                    'nhanh_order_status': order['statusCode'].lower(),
                    'name_customer': name_customer,
                    'note': '#MN linhqq',
                    'note_customer': order['description'],
                    'x_sale_chanel': 'online',
                    # 'carrier_name': order['carrierName'],
                    'user_id': user_id.id if user_id else None,
                    'team_id': team_id.id if team_id else None,
                    'company_id': default_company_id.id if default_company_id else None,
                    'warehouse_id': location_id.warehouse_id.id if location_id and location_id.warehouse_id else None,
                    'delivery_carrier_id': delivery_carrier_id.id,
                    'order_line': order_line,
                    'nhanh_customer_phone': order['customerMobile'],
                    'source_id': utm_source_id.id if utm_source_id else None,
                }
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

                value.update({
                    "x_voucher": x_voucher,
                    "x_code_voucher": x_code_voucher
                })
                
                # đổi trả hàng
                if order_returned or is_create_wh_in:
                    origin_order_id = request.env['sale.order'].sudo().search(
                        [('nhanh_id', '=', order.get('returnFromOrderId', order.get('id', 0)))], limit=1)
                    value.update({
                        'x_is_return': True,
                        'x_origin': origin_order_id.id if origin_order_id else None,
                        'nhanh_origin_id': order.get('returnFromOrderId', 0)
                    })
                webhook_value_id.order_id = self.sale_order_model().sudo().create(value)

                if is_create_wh_in or order_returned:
                    try:
                        webhook_value_id.order_id.with_context({"wh_in":True}).action_create_picking()
                    except:
                        pass

                elif data['status'] in ['Canceled', 'Aborted']:
                    if webhook_value_id.order_id.picking_ids and 'done' not in webhook_value_id.order_id.picking_ids.mapped(
                            'state'):
                        for picking_id in odoo_order.picking_ids:
                            picking_id.action_cancel()
                else:
                    if data['status'] in ["Packing", "Pickup", "Shipping", "Success"] and not webhook_value_id.order_id.picking_ids:
                        try:
                            webhook_value_id.order_id.check_sale_promotion()
                            webhook_value_id.order_id.action_create_picking()
                        except:
                            return self.result_request(200, 0, _('Create sale order success'))

                return self.result_request(200, 0, _('Create sale order success'))
            else:
                if data.get('status'):
                    odoo_order.sudo().write({
                        'nhanh_order_status': data['status'].lower(),
                    })
                    if data['status'] in ["Packing", "Pickup", "Shipping", "Success"] and not odoo_order.picking_ids:
                        try:
                            odoo_order.check_sale_promotion()
                            odoo_order.action_create_picking()
                        except Exception as e:
                            pass
                        
                    elif data['status'] in ['Canceled', 'Aborted', 'CarrierCanceled']:
                        if odoo_order.picking_ids and 'done' not in odoo_order.picking_ids.mapped('state'):
                            for picking_id in odoo_order.picking_ids:
                                picking_id.action_cancel()
                        odoo_order.with_context({'disable_cancel_warning': True}).action_cancel()
                    return self.result_request(200, 0, _('Update sale order success'))
                else:
                    return self.result_request(404, 1, _('Update sale order false'))
        # elif event_type == 'orderDelete':
        #     for item in data:
        #         order_ids = self.sale_order_model().sudo().search([('nhanh_id', '=', int(item))]).sudo()
        #         order_ids.write({
        #             'state': 'cancel',
        #             'nhanh_order_status': 'canceled',
        #         })
        #         for order_id in order_ids:
        #             if not order_id.picking_ids:
        #                 continue
        #             if 'done' in order_id.picking_ids.mapped('state'):
        #                 continue
        #             order_id.picking_ids.unlink()
        #     return self.result_request(200, 0, _('Delete sale order success'))

    # End Create Category

    def webhook_enable(self, event_type, data):
        return self.result_request(200, 0, _('Webhook enable success'))

    def partner_model(self):
        return request.env['res.partner']

    def store_first_order_model(self):
        return request.env['store.first.order']

    def store_model(self):
        return request.env['store']

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
