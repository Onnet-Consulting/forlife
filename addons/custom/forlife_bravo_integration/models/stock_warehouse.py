# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField


class StockWarehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ['stock.warehouse', 'bravo.model']
    _bravo_table = 'B20Warehouse'

    br1 = BravoCharField(odoo_name='warehouse_code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name', identity=True)
    br3 = BravoMany2oneField('res.partner', odoo_name='partner_id', bravo_name='Address',
                             field_detail='contact_address_complete')
    br4 = BravoMany2oneField('res.company', odoo_name='company_id', bravo_name='CompanyCode', field_detail='code')
