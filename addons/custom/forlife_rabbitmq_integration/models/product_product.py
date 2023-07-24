# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.detailed_type == 'product')

    def get_sync_info_value(self):
        return [{
            'id': line.id,
            'created_at': line.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': line.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'product_code': line.sku_code or None,
            'sku': line.barcode or None,
            'name': line.name or None,
            'unit': line.uom_id.name or None,
            'price': line.lst_price or None,
            'active': line.active,
            'sale_ok': line.sale_ok,
            'category': {
                'id': line.categ_id.id,
                'parent_id': line.categ_id.parent_id.id or None,
                'name': line.categ_id.name,
                'code': line.categ_id.category_code,
            } if line.categ_id else None,
            'attributes': [
                {
                    'id': attr.attribute_id.id,
                    'name': attr.attribute_id.name or None,
                    'code': attr.attribute_id.attrs_code or None,
                    'value': {
                        'id': attr.value_ids.id,
                        'name': attr.value_ids.name or None,
                        'code': attr.value_ids.code or None
                    }
                } for attr in line.attribute_line_ids
            ]
        } for line in self]

    @api.model
    def get_field_update(self):
        return ['sku_code', 'barcode', 'active']
