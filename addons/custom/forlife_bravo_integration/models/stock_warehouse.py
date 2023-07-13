# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField, BravoIntegerField


class StockWarehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ['stock.warehouse', 'bravo.model']
    _bravo_table = 'B20Warehouse'
    _bravo_field_sync = ['code', 'name', 'company_id', 'warehouse_gr_id']

    br1 = BravoCharField(odoo_name='code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoMany2oneField('res.company', odoo_name='company_id', bravo_name='CompanyCode', field_detail='code')
    br4 = BravoIntegerField(bravo_default=0, bravo_name="IsGroup")
    br5 = BravoMany2oneField('warehouse.group', odoo_name='warehouse_gr_id', bravo_name='WarehouseGroup',
                             field_detail='code_level_1')
