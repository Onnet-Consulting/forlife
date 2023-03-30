# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import *

class AccountTax(models.Model):
    _inherit = 'account.tax'


    br_1 = fields.BravoCharField()