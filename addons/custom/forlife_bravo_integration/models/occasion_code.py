# -*- coding:utf-8 -*-

from ..fields import *


class OccasionCode(models.Model):
    _name = 'occasion.code'
    _inherit = ['occasion.code', 'bravo.model']
    _bravo_table = 'B20Job'
    _bravo_field_sync = ['code', 'name', 'company_id', 'group_id']

    br1 = BravoCharField(odoo_name='code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoIntegerField(bravo_default=0, bravo_name='IsGroup')
    br4 = BravoMany2oneField('res.company', odoo_name='company_id', bravo_name='CompanyCode', field_detail='code')
    br5 = BravoMany2oneField('occasion.group', odoo_name='group_id', bravo_name='ParentCode', field_detail='name')


class OccasionGroup(models.Model):
    _name = 'occasion.group'
    _inherit = ['occasion.group', 'bravo.model']
    _bravo_table = 'B20Job'
    _bravo_field_sync = ['name', 'description']

    br1 = BravoCharField(odoo_name='name', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='description', bravo_name='Name')
    br3 = BravoIntegerField(bravo_default=1, bravo_name='IsGroup')
