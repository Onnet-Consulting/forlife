# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class ProductAttributeValue(models.Model):
    _name = 'product.attribute.value'
    _inherit = ['product.attribute.value', 'bravo.model']
    _bravo_table = 'B20Season'
    _bravo_field_sync = ['name', 'code']

    br1 = BravoCharField(odoo_name="code", bravo_name="Code", identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')

    def bravo_filter_records(self):
        records = super().bravo_filter_records()
        attr_value = self.env['res.utility'].get_attribute_code_config()
        return records.filtered(lambda rec: rec.attribute_id.attrs_code == attr_value.get('mua_vu'))
