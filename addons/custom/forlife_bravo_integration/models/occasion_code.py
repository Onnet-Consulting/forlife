# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import *


class OccasionCode(models.Model):
    _name = 'occasion.code'
    _inherit = ['occasion.code', 'bravo.model']

    