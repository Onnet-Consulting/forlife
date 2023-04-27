# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'sync.info.rabbitmq.update']
    _update_action = 'update_product'

    def check_update_info(self, values):
        if not self.mapped('product_variant_ids'):
            return False
        field_check_update = ['name', 'uom_id', 'categ_id', 'list_price']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'list_price': 'price',
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
        for product in self.mapped('product_variant_ids'):
            vals.update({
                'id': product.id,
                'updated_at': product.product_tmpl_id.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.extend([copy.copy(vals)])
        return data
