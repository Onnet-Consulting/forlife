# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.nhanh_connector.models import constant
from odoo import api, fields, models, _, exceptions
import logging

_logger = logging.getLogger(__name__)


class NhanhWebhookValue(models.Model):
    _name = 'nhanh.webhook.value'
    _description = 'Nhanh webhook value for re-sync'

    event_type = fields.Selection([
        ('order_add', 'Add Order'),
        ('order_update', 'Update Order'),
        ('order_delete', 'Delete Order'),
    ], 'Event Type')
    event_value = fields.Text('Event Value')
    error = fields.Char('Error')
    state = fields.Selection([('fail', 'Fail'), ('done', 'Done')], 'State', default='fail')

    def action_retry(self):
        data = self.event_value
        if self.event_type == 'order_add':
            self.action_order_add(data)
        elif self.event_type == 'order_update':
            self.action_order_update(data)
        elif self.event_type == 'order_delete':
            self.action_order_delete(data)

    def action_order_add(self, data):
        order = constant.get_order_from_nhanh(self, data.get('data', {}).get('orderId', 0))
        if not order:
            self.write({
                'error': f"{self.error if self.error else ''} \n Không lấy được thông tin đơn hàng từ Nhanh"
            })
            return
        try:
            name_customer = False
            # Add customer if not existed
            nhanh_partner = self.env['res.partner'].sudo().search(
                [('code_current_customers', '=', 'code_current_customers_nhanhvn')], limit=1)
            if not nhanh_partner:
                nhanh_partner = self.env['res.partner'].sudo().create({
                    'code_current_customers': 'code_current_customers_nhanhvn',
                    'name': 'Nhanh.Vn',
                    'customer_rank': 1
                })
            partner = self.env['res.partner'].sudo().search(
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
                partner = self.env['res.partner'].sudo().create(partner_value)
            order_line = []
            location_id = self.env['stock.location'].search([('nhanh_id', '=', int(order['depotId']))], limit=1)
            for item in data['products']:
                product = self.product_template_model().sudo().search([('nhanh_id', '=', item.get('id'))], limit=1)
                product_product = self.env['product.product'].sudo().search([('product_tmpl_id', '=', product.id)],
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
            user_id = self.env['res.users'].search([('partner_id.name', '=', order['saleName'])], limit=1)
            # đội ngũ bán hàng
            team_id = self.env['crm.team'].search([('name', '=', order['trafficSourceName'])], limit=1)
            default_company_id = self.env['res.company'].sudo().search([('code', '=', '1300')], limit=1)
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
                origin_order_id = self.env['sale.order'].sudo().search(
                    [('nhanh_id', '=', order.get('returnFromOrderId', 0))], limit=1)
                value.update({
                    'x_is_return': True,
                    'x_origin': origin_order_id.id if origin_order_id else None,
                    'nhanh_origin_id': order.get('returnFromOrderId', 0)
                })
            self.self.env['sale.order'].sudo().create(value)
        except Exception as ex:
            self.write({
                'error': f"{self.error if self.error else ''} \n {ex}"
            })
            return

    def action_order_update(self, data):
        if data.get('status'):
            order = self.env['sale.order'].sudo().search([('nhanh_id', '=', data.get('orderId'))], limit=1)
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

    def action_order_delete(self, data):
        for item in data:
            order_ids = self.env['sale.order'].sudo().search([('nhanh_id', '=', int(item))])
            order_ids.sudo().write({
                'state': 'cancel',
                'nhanh_order_status': 'canceled',
            })
            for order_id in order_ids:
                if not order_id.picking_ids:
                    continue
                if 'done' in order_id.picking_ids.mapped('state'):
                    continue
                order_id.picking_ids.unlink()
