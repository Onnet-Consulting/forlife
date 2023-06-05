# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField


class AnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['account.analytic.account', 'bravo.model']
    _bravo_table = 'B20Dept'

    br1 = BravoCharField(odoo_name="code", bravo_name="Code", identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
