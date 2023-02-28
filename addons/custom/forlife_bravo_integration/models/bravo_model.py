# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.tools.float_utils import float_round
from datetime import date, datetime, time

Default = object()


class BravoModel(models.AbstractModel):
    _name = 'bravo.model'

    def get_data(self):
        pass

    def generate_sql(self):
        pass
