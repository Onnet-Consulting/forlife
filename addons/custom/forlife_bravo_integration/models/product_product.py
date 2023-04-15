# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'bravo.model']
    _bravo_table = 'B20Item'

    br1 = BravoCharField(odoo_name="barcode", bravo_name="Code", identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoMany2oneField('uom.uom', odoo_name='uom_id', bravo_name='Unit', field_detail='name')
