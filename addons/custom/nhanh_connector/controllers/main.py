import datetime

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

    @http.route('/nhanh/webhook/handler_tokyo', type='http', auth='public', methods=['POST'], csrf=False)
    def nhanh_webhook_handler_tokyo(self, **post):
        value = json.loads(request.httprequest.data)
        business_id = value.get("businessId")
        request.business_id = business_id

        event_type = value.get('event')
        _logger.info(f'Webhook nhanh called value: {value}, time: {datetime.datetime.now()}')
        if event_type in ['orderUpdate']:
            webhook_value_id = request.env['nhanh.webhook.value'].sudo().create({
                'event_type': event_type_mapping.get(event_type, ''),
                'event_value': value,
                'nhanh_id': value.get('data').get('orderId'),
                'state_nhanh': value.get('data').get('status'),
                'brand': str(value.get('businessId')),
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
                _logger.info(f'Webhook to system odoo false {ex}')
                if webhook_value_id:
                    webhook_value_id.update({
                        'error': ex
                    })
                result_requests = self.result_request(404, 0, _('Webhook to system odoo false'))
            return request.make_response(json.dumps(result_requests),
                                         headers={'Content-Type': 'application/json'})

    @http.route('/nhanh/webhook/handler_format', type='http', auth='public', methods=['POST'], csrf=False)
    def nhanh_webhook_handler_format(self, **post):
        value = json.loads(request.httprequest.data)
        business_id = value.get("businessId")
        request.business_id = business_id

        event_type = value.get('event')
        _logger.info(f'Webhook nhanh called value: {value}, time: {datetime.datetime.now()}')
        if event_type in ['orderUpdate']:
            webhook_value_id = request.env['nhanh.webhook.value'].sudo().create({
                'event_type': event_type_mapping.get(event_type, ''),
                'event_value': value,
                'nhanh_id': value.get('data').get('orderId'),
                'state_nhanh': value.get('data').get('status'),
                'brand': str(value.get('businessId')),
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
                _logger.info(f'Webhook to system odoo false {ex}')
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
        default_company_id = n_client.get_company()
        if not default_company_id:
            return self.result_request(404, 1, _('Chọn company trước khi đồng bộ đơn hàng từ Nhanh.Vn, Vui lòng vào Thiết lập -> Kế toán để chọn company'))


        try:
            order = n_client.get_order_from_nhanh_id(order_id, brand_id)
        except Exception as e:
            order = None

        if not order:
            return self.result_request(404, 1, _('Không lấy được thông tin đơn hàng từ Nhanh'))

        order_status_skip = [
            'New', 
            'Confirming', 
            'CustomerConfirming',
            'ChangeDepot',
            'SoldOut'
        ]
        if event_type == 'orderUpdate':
            odoo_order = n_client.get_sale_order(order_id)
            # luong return v2, khong tao SO tra hang chi tao phieu tra hang tu picking
            if odoo_order and data['status'] in ['Returned', 'Canceled']:
                odoo_order.create_picking_return(nhanh_status=data['status'])
                return self.result_request(200, 0, _('Update sale order success'))
            is_create_wh_in = False
            if odoo_order and data['status'] in ['Returned']:
                origin_order_id = odoo_order
                odoo_order = None
                is_create_wh_in = True
                nhanh_origin_id = order_id
            partial_order_returned = order.get('returnFromOrderId', 0)
            order_returned = order.get('returnFromOrderId', 0) and data['status'] == 'Success'

            if not is_create_wh_in:
                if partial_order_returned:
                    if not order_returned:
                        return self.result_request(200, 0, _('Update sale order success'))

                elif data['status'] in order_status_skip:
                    return self.result_request(404, 1, _('Order confirmation is required'))

            if not odoo_order:
                # với trạng thái này thì không tạo so
                if data['status'] in ['Canceled', 'Aborted', 'CarrierCanceled']:
                    return self.result_request(200, 0, _('Success'))

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

                
                # đổi trả hàng
                if order_returned or is_create_wh_in:
                    if not is_create_wh_in:
                        origin_order_id = request.env['sale.order'].sudo().search([
                            ('nhanh_id', '=', order.get('returnFromOrderId', order.get('id', 0)))
                        ], limit=1)
                        nhanh_origin_id = order.get('returnFromOrderId', 0)

                    order_data.update({
                        'x_is_return': True,
                        'x_origin': origin_order_id.id if origin_order_id else None,
                        'nhanh_origin_id': nhanh_origin_id
                    })
                webhook_value_id.order_id = self.sale_order_model().sudo().create(order_data)

                if is_create_wh_in or order_returned:
                    try:
                        webhook_value_id.order_id.create_stock_picking_so_from_nhanh_with_return_so()
                    except Exception as e:
                        print(str(e))
                # bỏ phân logi bên dưới
                elif data['status'] in ['Canceled', 'Aborted', 'CarrierCanceled']:
                    if webhook_value_id.order_id.picking_ids:
                        for picking_id in webhook_value_id.order_id.picking_ids:
                            if picking_id.state != 'done':
                                picking_id.action_cancel()
                            # else:
                            #     if picking_id.company_id.id == webhook_value_id.order_id.company_id.id:
                            #         try:
                            #             picking_id.create_invoice_out_refund()
                            #         except Exception as e:
                            #             picking_id.message_post(body=str(e))

                else:
                    if data['status'] in ["Packing", "Pickup", "Shipping", "Success", "Packed"]:
                        webhook_value_id.order_id.check_sale_promotion()
                        if data['status'] in ["Success"]:
                            try:
                                # webhook_value_id.order_id.action_create_picking()
                                webhook_value_id.order_id.action_confirm()
                                webhook_value_id.order_id.picking_ids.with_context(super=True).confirm_from_so(True)
                            except:
                                return self.result_request(200, 0, _('Create sale order success'))
                        elif webhook_value_id.order_id.state != 'check_promotion' and not webhook_value_id.order_id.picking_ids:
                            try:
                                # webhook_value_id.order_id.action_create_picking()
                                webhook_value_id.order_id.action_confirm()
                            except:
                                return self.result_request(200, 0, _('Create sale order success'))

                return self.result_request(200, 0, _('Create sale order success'))
            else:
                if data.get('status'):
                    odoo_order.sudo().write({
                        'nhanh_order_status': data['status'].lower(),
                    })
                    if data['status'] in ["Packing", "Pickup", "Shipping", "Packed"]:
                        odoo_order.check_sale_promotion()
                        if odoo_order.state != 'check_promotion' and not odoo_order.picking_ids:
                            try:
                                # odoo_order.action_create_picking()
                                odoo_order.action_confirm()
                            except Exception as e:
                                return self.result_request(404, 1, _('Update sale order false'))
                    if data['status'] in ["Success"]:
                        if odoo_order.state == 'draft':
                            odoo_order.action_confirm()
                        odoo_order.picking_ids.with_context(super=True).confirm_from_so(True)

                    elif data['status'] in ['Canceled', 'Aborted', 'CarrierCanceled']:
                        if odoo_order.picking_ids:
                            for picking_id in odoo_order.picking_ids:
                                if picking_id.state != 'done':
                                    picking_id.action_cancel()
                                # else:
                                #     if picking_id.company_id.id == odoo_order.company_id.id:
                                #         try:
                                #             picking_id.create_invoice_out_refund()
                                #         except Exception as e:
                                #             picking_id.message_post(body=str(e))

                        # if odoo_order.picking_ids and 'done' not in odoo_order.picking_ids.mapped('state'):
                        #     for picking_id in odoo_order.picking_ids:
                        #         picking_id.action_cancel()
                        try:
                            odoo_order.with_context({'disable_cancel_warning': True}).action_cancel()
                        except Exception as e:
                            pass

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
