# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class AssetLocation(models.Model):
    _name = 'asset.location'
    _inherit = ['asset.location', 'bravo.model']
    _bravo_table = 'B20Location'
    _bravo_field_sync = ['name', 'code', 'address']

    br1 = BravoCharField(odoo_name='code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoCharField(odoo_name='address', bravo_name='Address')
