# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoIntegerField, BravoDatetimeField, BravoDateField, BravoMany2oneField, \
    BravoSelectionField


class ExpenseCategory(models.Model):
    _name = 'expense.category'
    _inherit = ['expense.category', 'bravo.model']
    _bravo_table = 'B20ExpenseCatg'
    _bravo_field_sync = ['name', 'code']

    br1 = BravoCharField(odoo_name='code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoIntegerField(bravo_default=1, bravo_name="IsGroup")


class ExpenseItem(models.Model):
    _name = 'expense.item'
    _inherit = ['expense.item', 'bravo.model']
    _bravo_table = 'B20ExpenseCatg'
    _bravo_field_sync = ['name', 'code', 'group_id']

    br_1 = BravoCharField(odoo_name="code", bravo_name="Code", identity=True)
    br_2 = BravoCharField(odoo_name="name", bravo_name="Name")
    br_3 = BravoIntegerField(bravo_default=0, bravo_name="IsGroup")
    br_4 = BravoMany2oneField('expense.category', odoo_name='group_id', bravo_name='ParentCode', field_detail='code')
