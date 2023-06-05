# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.detailed_type == 'product')

    def get_sync_create_data(self):
        data = []
        for product in self:
            vals = {
                'id': product.id,
                'created_at': product.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': product.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'product_code': product.sku_code or None,
                'sku': product.barcode or None,
                'name': product.name or None,
                'unit': product.uom_id.name or None,
                'price': product.lst_price or None,
                'active': product.active,
                'sale_ok': product.sale_ok,
                'category': {
                    'id': product.categ_id.id,
                    'parent_id': product.categ_id.parent_id.id or None,
                    'name': product.categ_id.name,
                    'code': product.categ_id.category_code,
                } if product.categ_id else None,
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
                    } for attr in product.product_template_attribute_value_ids
                ]
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['sku_code', 'barcode', 'active']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'barcode': 'sku',
            'active': 'active',
            'sku_code': 'product_code',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        data = []
        for product in self:
            vals.update({
                'id': product.id,
                'updated_at': product.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.extend([copy.copy(vals)])
        return data
