# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class ForLifeProduction(models.Model):
    _name = 'forlife.production'
    _inherit = ['forlife.production', 'bravo.model']
    _bravo_table = 'B30StatsDoc'

    br1 = BravoMany2oneField("res.company", odoo_name="company_id", bravo_name="CompanyCode",
                             field_detail="code")
    br2 = BravoCharField(odoo_name="code", bravo_name="DocNo", identity=True)
    br3 = BravoDatetimeField(odoo_name="create_date", bravo_name="DocDate")
    br4 = BravoCharField(odoo_name="name", bravo_name="Name")
    br5 = BravoDateField(odoo_name="produced_from_date", bravo_name="StartDate")
    br6 = BravoDateField(odoo_name="to_date", bravo_name="EndDate")
