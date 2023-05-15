# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_create_data(self):
        data = []
        for order in self:
            data.append({
                'id': f'sale_order_{order.id}',
                'order_code': 'PBB',
                'created_at': order.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': order.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'customer_note': None,
                'internal_note': order.note or None,
                'status': self.env['ir.model.fields'].search([('model_id', '=', self.env['ir.model'].search(
                    [('model', '=', self._name)]).id), ('name', '=', 'state')]).selection_ids.filtered(lambda x: x.value == order.state).name,
                'products': [
                    {
                        'product_id': line.product_id.id,
                        'sku': line.product_id.default_code or None,
                        'name': line.product_id.name or None,
                        'quantity': line.product_uom_qty,
                        'order_price': line.price_unit,
                        'discount_amount': line.discount * line.product_uom_qty * line.price_unit / 100,
                        'total_price': line.price_subtotal,
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
                            } for attr in line.product_id.product_template_variant_value_ids
                        ],
                        'weight': f'{line.product_id.weight} {line.product_id.weight_uom_name}',
                        'volume': f'{line.product_id.volume} {line.product_id.volume_uom_name}',
                    } for line in order.order_line
                ],
                'total_price': order.amount_total,
                'store': {
                    'store_id': order.warehouse_id.id or None,
                    'store_name': order.warehouse_id.name or None,
                },
                'customer': {
                    'id': order.partner_id.id,
                    'phone_number': order.partner_id.phone,
                    'name': order.partner_id.name,
                } if order.partner_id else None,
                'payment_method': ['cod'],
                'order_date': order.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                'coupons': None,
            })
        return data

    def check_update_info(self, values):
        field_check_update = ['note', 'state', 'order_line', 'warehouse_id', 'partner_id', 'order_date']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        data = []
        for order in self:
            vals = {
                'id': f'sale_order_{order.id}',
                'updated_at': order.write_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            if 'note' in field_update:
                vals.update({'internal_note': order.note or None})
            if 'order_date' in field_update:
                vals.update({'order_date': order.date_order.strftime('%Y-%m-%d %H:%M:%S')})
            if 'state' in field_update:
                vals.update({'status': self.env['ir.model.fields'].search([('model_id', '=', self.env['ir.model'].search(
                    [('model', '=', self._name)]).id), ('name', '=', 'state')]).selection_ids.filtered(lambda x: x.value == order.state).name})
            if 'order_line' in field_update:
                vals.update({
                    'products': [
                        {
                            'product_id': line.product_id.id,
                            'sku': line.product_id.default_code or None,
                            'name': line.product_id.name or None,
                            'quantity': line.product_uom_qty,
                            'order_price': line.price_unit,
                            'discount_amount': line.discount * line.product_uom_qty * line.price_unit / 100,
                            'total_price': line.price_subtotal,
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
                                } for attr in line.product_id.product_template_variant_value_ids
                            ],
                            'weight': f'{line.product_id.weight} {line.product_id.weight_uom_name}',
                            'volume': f'{line.product_id.volume} {line.product_id.volume_uom_name}',
                        } for line in order.order_line
                    ],
                    'total_price': order.amount_total,
                })
            if 'warehouse_id' in field_update:
                vals.update({
                    'store': {
                        'store_id': order.warehouse_id.id or None,
                        'store_name': order.warehouse_id.name or None,
                    }
                })
            if 'partner_id' in field_update:
                vals.update({
                    'customer': {
                        'id': order.partner_id.id,
                        'phone_number': order.partner_id.phone,
                        'name': order.partner_id.name,
                    } if order.partner_id else None,
                })
            data.extend([copy.copy(vals)])
        return data

    def action_delete_record(self, record_ids):
        data = [{'id': f'sale_order_{res_id}'} for res_id in record_ids]
        if data:
            self.push_message_to_rabbitmq(data, self._delete_action, self._name)
