# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class AssetsAssets(models.Model):
    _name = 'assets.assets'
    _inherit = ['assets.assets', 'bravo.model']
    _bravo_table = 'B20Product'
    _bravo_field_sync = ['name', 'code', 'unit']

    bravo_create_date = fields.Datetime(
        readonly=True,
        help='This datetime will be save in database in UTC+7 format - timezone (Asia/Ho_Chi_Minh)\n'
             'This value is synchronized between bravo and Odoo, not by normal Odoo action \n'
             'so the datetime will not be convert to UTC value like normally')
    bravo_write_date = fields.Datetime(
        readonly=True,
        help='As same the bravo_create_date field - this field will be updated when wizard liquidation asset run')

    br1 = BravoCharField(odoo_name='code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoCharField(odoo_name='unit', bravo_name='UnitCode')

    @api.model
    def bravo_get_filter_domain(self, **kwargs):
        """Get domain to filter records before execute any action"""
        return [('type', '=', 'XDCB')]
