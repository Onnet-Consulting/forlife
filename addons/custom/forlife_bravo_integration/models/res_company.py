# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'bravo.model']
    _bravo_table = 'B00Branch'

    br1 = BravoCharField(odoo_name='code', bravo_name='BranchCode', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='BranchName')
