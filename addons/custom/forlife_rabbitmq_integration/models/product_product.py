# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _create_action = 'create_product'
    _update_action = 'update_product'
    _delete_action = 'delete_product'

    def get_sync_create_data(self):
        data = []
        for product in self:
            vals = {
                'id': product.id,
                'created_at': product.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': product.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'sku': product.default_code or None,
                'barcode': product.barcode or None,
                'name': product.name or None,
                'unit': product.uom_id.name or None,
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
                    } for attr in product.product_template_variant_value_ids
                ]
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['default_code', 'barcode', 'name', 'uom_id', 'categ_id']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'default_code': 'sku',
            'barcode': 'barcode',
            'name': 'name',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        if 'uom_id' in values:
            uom = self.env['uom.uom'].search_read([('id', '=', values.get('uom_id'))], ['name'])
            vals['unit'] = uom[0].get('name') if uom else None
        if 'categ_id' in values:
            category = self.env['product.category'].search([('id', '=', values.get('categ_id'))], limit=1)
            vals['category'] = {
                'id': category.id,
                'parent_id': category.parent_id.id or None,
                'name': category.name,
                'code': category.category_code,
            } if category else None
        data = []
        for product in self:
            vals.update({
                'id': product.id,
                'updated_at': product.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.append(vals)
        return data
