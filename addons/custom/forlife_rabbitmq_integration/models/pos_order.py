# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': f'pos_order_{line.id}',
            'order_code': 'PBL',
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'customer_note': None,
            'internal_note': line.note or None,
            'status': self.env['ir.model.fields'].search([('model_id', '=', self.env['ir.model'].search(
                [('model', '=', self._name)]).id), ('name', '=', 'state')]).selection_ids.filtered(lambda x: x.value == line.state).name,
            'products': [
                {
                    'product_id': order_line.product_id.id,
                    'sku': order_line.product_id.barcode or None,
                    'name': order_line.product_id.name or None,
                    'quantity': order_line.qty,
                    'order_price': order_line.price_unit,
                    'discount_amount': order_line.money_is_reduced,
                    'total_price': order_line.price_subtotal_incl,
                    'attributes': [
                        {
                            'id': attr.attribute_id.id,
                            'name': attr.attribute_id.name or None,
                            'code': attr.attribute_id.attrs_code or None,
                            'value': {
                                'id': attr.product_attribute_value_id.id,
                                'name': attr.product_attribute_value_id.name or None,
                                'code': attr.product_attribute_value_id.code or None
                            }
                        } for attr in order_line.product_id.product_template_attribute_value_ids
                    ],
                    'weight': f'{order_line.product_id.weight} {order_line.product_id.weight_uom_name}',
                    'volume': f'{order_line.product_id.volume} {order_line.product_id.volume_uom_name}',
                } for order_line in line.lines
            ],
            'total_price': line.amount_total,
            'store': {
                'store_id': line.config_id.store_id.warehouse_id.id or None,
                'store_name': line.config_id.store_id.warehouse_id.name or None,
            },
            'customer': {
                'id': line.partner_id.id,
                'phone_number': line.partner_id.phone,
                'name': line.partner_id.name,
            } if line.partner_id else None,
            'payment_method': [pay.payment_method_id.name for pay in line.payment_ids],
            'order_date': line.date_order.strftime('%Y-%m-%d %H:%M:%S'),
            'payment_date': line.date_order.strftime('%Y-%m-%d %H:%M:%S'),
            'delivery_date': line.date_order.strftime('%Y-%m-%d %H:%M:%S'),
            'complete_date': line.date_order.strftime('%Y-%m-%d %H:%M:%S'),
            'coupons': [coupon.name for coupon in line.mapped('lines.promotion_usage_ids.code_id')] or None,
            'brand': line.brand_id.name or None,
        } for line in self]

    def action_delete_record(self, record_ids):
        data = [{'id': f'pos_order_{res_id}'} for res_id in record_ids]
        if data:
            self.push_message_to_rabbitmq(data, self._delete_action, self._name)
