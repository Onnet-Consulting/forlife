# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = ['stock.location', 'bravo.model']
    _bravo_table = 'B20TransferType'
    _bravo_field_sync = ['code', 'name']

    br1 = BravoCharField(odoo_name="code", bravo_name="Code", identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')

    @api.model
    def bravo_get_filter_domain(self, **kwargs):
        return [('reason_type_id', '!=', False)]
