# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def get_sync_info_value(self):
        return [{
            'id': f'sale_order_{line.id}',
            'order_code': 'PBB',
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'customer_note': None,
            'internal_note': line.note or None,
            'status': self.env['ir.model.fields'].search([('model_id', '=', self.env['ir.model'].search(
                [('model', '=', self._name)]).id), ('name', '=', 'state')]).selection_ids.filtered(lambda x: x.value == line.state).name,
            'products': [
                {
                    'product_id': line.product_id.id,
                    'sku': line.product_id.barcode or None,
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
                        } for attr in line.product_id.product_template_attribute_value_ids
                    ],
                    'weight': f'{line.product_id.weight} {line.product_id.weight_uom_name}',
                    'volume': f'{line.product_id.volume} {line.product_id.volume_uom_name}',
                } for line in line.order_line
            ],
            'total_price': line.amount_total,
            'store': {
                'store_id': line.warehouse_id.id or None,
                'store_name': line.warehouse_id.name or None,
            },
            'customer': {
                'id': line.partner_id.id,
                'phone_number': line.partner_id.phone,
                'name': line.partner_id.name,
            } if line.partner_id else None,
            'payment_method': ['cod'],
            'order_date': line.date_order.strftime('%Y-%m-%d %H:%M:%S'),
            'coupons': None,
            'nhanh_order': line.source_record or False,
            'nhanh_order_status': line.nhanh_order_status or None,
        } for line in self]

    @api.model
    def get_field_update(self):
        return ['note', 'state', 'order_line', 'warehouse_id', 'partner_id', 'order_date', 'nhanh_order', 'nhanh_order_status']

    def action_delete_record(self, record_ids):
        data = [{'id': f'sale_order_{res_id}'} for res_id in record_ids]
        if data:
            self.push_message_to_rabbitmq(data, self._delete_action, self._name)
