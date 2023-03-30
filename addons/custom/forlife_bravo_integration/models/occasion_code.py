# -*- coding:utf-8 -*-

from ..fields import *


class OccasionCode(models.Model):
    _name = 'occasion.code'
    _inherit = ['occasion.code', 'bravo.model']
    _bravo_table = 'B20Job'

    br1 = BravoCharField(odoo_name='code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')
    br3 = BravoMany2oneField('res.company', odoo_name='company_id', bravo_name='CompanyCode', field_detail='code')
