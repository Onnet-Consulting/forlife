# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.safe_eval import safe_eval
from odoo.addons.nhanh_connector.models import constant
from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError
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
        data = safe_eval(self.event_value)
        if self.event_type == 'order_add':
            self.action_order_add(data)
        elif self.event_type == 'order_update':
            self.action_order_update(data)
        elif self.event_type == 'order_delete':
            self.action_order_delete(data)

    def action_order_add(self, data):
        data = data.get('data', {})
        order = constant.get_order_from_nhanh_id(self, data.get('orderId', 0))
        if not order:
            self.write({
                'error': f"Không lấy được thông tin đơn hàng từ Nhanh"
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
            location_id = self.env['stock.location'].sudo().search([('nhanh_id', '=', int(order['depotId']))], limit=1)
            for item in data['products']:
                product_id = self.env['product.product'].sudo().search([('nhanh_id', '=', item.get('id'))], limit=1)
                if not product_id:
                    raise ValidationError('Không có sản phẩm có id nhanh là %s' % item.get('id'))
                order_line.append((
                    0, 0, {'product_template_id': product_id.product_tmpl_id.id, 'product_id': product_id.id,
                           'name': product_id.name,
                           'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
                           'product_uom': product_id.uom_id.id if product_id.uom_id else self.uom_unit(),
                           'customer_lead': 0, 'sequence': 10, 'is_downpayment': False, 'x_location_id': location_id.id,
                           'discount': float(item.get('discount')) / float(item.get('price')) * 100 if item.get(
                               'discount') else 0,
                           'x_cart_discount_fixed_price': float(item.get('discount')) * float(
                               item.get('quantity')) if item.get('discount') else 0}))

            status = 'draft'
            if data['status'] == 'Confirmed':
                status = 'draft'
            elif data['status'] in ['Packing', 'Pickup']:
                status = 'sale'
            elif data['status'] in ['Shipping', 'Returning']:
                status = 'sale'
            elif data['status'] == 'Success':
                status = 'done'
            elif data['status'] == 'Canceled':
                status = 'cancel'

            # nhân viên kinh doanh
            user_id = self.env['res.users'].sudo().search([('partner_id.name', '=', order['saleName'])], limit=1)
            # đội ngũ bán hàng
            team_id = self.env['crm.team'].sudo().search([('name', '=', order['trafficSourceName'])], limit=1)
            default_company_id = self.env['res.company'].sudo().search([('code', '=', '1300')], limit=1)
            # warehouse_id = request.env['stock.warehouse'].search([('nhanh_id', '=', int(data['depotId']))], limit=1)
            # if not warehouse_id:
            #     warehouse_id = request.env['stock.warehouse'].search([('company_id', '=', default_company_id.id)], limit=1)
            value = {
                'nhanh_id': data['orderId'],
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
                'error': f"{ex}"
            })
            return

    def action_order_update(self, data):
        data = data.get('data', {})
        odoo_order = self.env['sale.order'].sudo().search([('nhanh_id', '=', data.get('orderId'))], limit=1)
        if not odoo_order:
            order, brand_id = constant.get_order_from_nhanh_id(self, data.get('orderId'))
            if not order:
                raise ValidationError('Không lấy được thông tin đơn hàng từ Nhanh')
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
                ['|', ('mobile', '=', order['customerMobile']), ('phone', '=', order['customerMobile'])],
                limit=1)
            if partner:
                name_customer = order['customerName']
            if not partner:
                partner_value = {
                    'phone': order['customerMobile'],
                    'mobile': order['customerMobile'],
                    'name': order['customerName'],
                    'email': order['customerEmail'],
                    'contact_address_complete': order['customerAddress'],
                    'customer_nhanh_id': order['customerId'],
                }
                partner = self.env['res.partner'].sudo().create(partner_value)
            order_line = []
            location_id = self.env['stock.location'].sudo().search([('nhanh_id', '=', int(order['depotId']))], limit=1)
            for item in data['products']:
                product_id = self.env['product.product'].sudo().search([('nhanh_id', '=', item.get('productId'))],
                                                                       limit=1)
                if not product_id:
                    raise ValidationError('Không có sản phẩm có id nhanh là %s' % item.get('productId'))
                order_line.append((
                    0, 0, {'product_template_id': product_id.product_tmpl_id.id, 'product_id': product_id.id,
                           'name': product_id.name,
                           'product_uom_qty': item.get('quantity'), 'price_unit': item.get('price'),
                           'product_uom': product_id.uom_id.id if product_id.uom_id else self.uom_unit(),
                           'customer_lead': 0, 'sequence': 10, 'is_downpayment': False, 'x_location_id': location_id.id,
                           'discount': float(item.get('discount')) / float(item.get('price')) * 100 if item.get(
                               'discount') else 0,
                           'x_cart_discount_fixed_price': float(item.get('discount')) * float(
                               item.get('quantity')) if item.get('discount') else 0}))

            # nhân viên kinh doanh
            user_id = self.env['res.users'].sudo().search([('partner_id.name', '=', order['saleName'])], limit=1)
            # đội ngũ bán hàng
            team_id = self.env['crm.team'].sudo().search([('name', '=', order['trafficSourceName'])], limit=1)
            default_company_id = self.env['res.company'].sudo().search([('code', '=', '1300')], limit=1)
            # warehouse_id = request.env['stock.warehouse'].search([('nhanh_id', '=', int(data['depotId']))], limit=1)
            # if not warehouse_id:
            #     warehouse_id = request.env['stock.warehouse'].search([('company_id', '=', default_company_id.id)], limit=1)
            value = {
                'nhanh_id': order['orderId'],
                'partner_id': nhanh_partner.id,
                'order_partner_id': partner.id,
                'nhanh_shipping_fee': order['shipFee'],
                'source_record': True,
                'code_coupon': order['couponCode'],
                'state': 'draft',
                'nhanh_order_status': order['statusCode'].lower(),
                'name_customer': name_customer,
                'note': order['privateDescription'],
                'note_customer': order['description'],
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
        else:
            if data.get('status'):
                odoo_order.sudo().write({
                    'nhanh_order_status': data['status'].lower(),
                })
                if data['status'] in ['Packing', 'Pickup']:
                    odoo_order.action_create_picking()
                elif data['status'] == 'Canceled':
                    if odoo_order.picking_ids and 'done' not in odoo_order.picking_ids.mapped('state'):
                        for picking_id in odoo_order.picking_ids:
                            picking_id.action_cancel()

    def action_order_delete(self, data):
        data = data.get('data', {})
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
