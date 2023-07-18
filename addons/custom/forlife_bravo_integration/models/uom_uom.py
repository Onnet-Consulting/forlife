# -*- coding:utf-8 -*-

from ..fields import *


class UomUom(models.Model):
    _name = 'uom.uom'
    _inherit = ['uom.uom', 'bravo.model']
    _bravo_table = 'B20Unit'
    _bravo_field_sync = ['code', 'name']

    br1 = BravoCharField(odoo_name='code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
