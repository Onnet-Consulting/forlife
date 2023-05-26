# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField, BravoIntegerField


class WarehouseGroup(models.Model):
    _name = 'warehouse.group'
    _inherit = ['warehouse.group', 'bravo.model']
    _bravo_table = 'B20Warehouse'

    br1 = BravoCharField(odoo_name='code_level_1', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoIntegerField(bravo_default=1, bravo_name="IsGroup")
    br4 = BravoMany2oneField('warehouse.group', odoo_name='parent_warehouse_group_id',
                             bravo_name='ParentCode', field_detail='code_level_1')
