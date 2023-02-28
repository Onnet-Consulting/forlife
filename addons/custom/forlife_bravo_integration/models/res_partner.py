# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'bravo.model']
    _bravo_table = 'B20Customer'

    br_1 = BravoCharField(odoo_name="name", bravo_name="Name")
    br_2 = BravoCharField(odoo_name="ref", bravo_name="Code")
    br_3 = BravoDatetimeField(odoo_name="create_date", bravo_name="Date")
