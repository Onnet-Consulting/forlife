# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'bravo.model']
    _bravo_table = 'B20Customer'

    br_1 = BravoCharField(odoo_name="ref", bravo_name="Code", identity=True)
    br_2 = BravoCharField(odoo_name="name", bravo_name="Name")
    br_3 = BravoCharField(odoo_name="phone", bravo_name="Tel")
    br_4 = BravoCharField(odoo_name="email", bravo_name="Email")
    br_5 = BravoCharField(odoo_name="vat", bravo_name="TaxRegNo")
