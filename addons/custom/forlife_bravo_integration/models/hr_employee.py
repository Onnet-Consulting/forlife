# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'bravo.model']
    _bravo_table = 'B20Employee'

    br1 = BravoCharField(odoo_name="code", bravo_name="Code", identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoMany2oneField('hr.department', odoo_name='department_id', bravo_name='DeptCode', field_detail='code')
    br4 = BravoDateField(odoo_name='birthday', bravo_name='BirthDate')
