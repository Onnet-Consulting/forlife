# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import *


class ResCurrencyRate(models.Model):
    _name = 'res.currency.rate'
    _inherit = ['res.currency.rate', 'bravo.model']

    br_1 = BravoMany2oneField('res.currency', odoo_name='currency_id', bravo_name='CurrencyCode', field_detail='name')
    br_2 = BravoCharField(odoo_name='name', bravo_name='StartDate')
    br_3 = BravoDecimalField(odoo_name='inverse_company_rate', bravo_name='BuyingExchangeRate')

    @api.model
    def bravo_get_default_insert_value(self):
        # special fields - don't declare them in Odoo
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def bravo_filter_records(self):
        res = super().bravo_filter_records()
        return res.filtered(lambda x: x.company_id.code == '1200')

    def bravo_get_update_values(self, values):
        return False

    def bravo_get_delete_sql(self):
        return False
