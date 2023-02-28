# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.fields import Default
from odoo.tools.float_utils import float_round
from datetime import date, datetime, time
from operator import attrgetter

MSSQL_DATE_FORMAT = '%Y-%m-%d'
MSSQL_TIME_FORMAT = '%H:%M:%S'


class BravoField(fields.Field):
    bravo_name = None
    odoo_name = None
    store = False

    _description_bravo_name = property(attrgetter('bravo_name'))
    _description_odoo_name = property(attrgetter('odoo_name'))

    def __int__(self, bravo_name=Default, odoo_name=Default, **kwargs):
        super(BravoField, self).__int__(bravo_name=bravo_name, odoo_name=odoo_name, **kwargs)

    def compute_value(self, record):
        return {self.bravo_name: record[self.odoo_name]}


class BravoCharField(BravoField, fields.Char):
    ...


class BravoIntegerField(BravoField, fields.Integer):
    ...


class BravoDecimalField(BravoField, fields.Float):
    precision_digits = 0

    def __int__(self, precision_digits=0, **kwargs):
        super(BravoField, self).__int__(precision_digits=precision_digits, **kwargs)

    def compute_value(self, record):
        res = super(BravoDecimalField, self).compute_value(record)
        key, value = res.popitem()
        value = value or 0.0
        precision_digits = self.precision_digits or 0
        return {key: float_round(value, precision_digits=precision_digits)}


class BravoDateField(BravoField, fields.Date):
    ...


class BravoDatetimeField(BravoField, fields.Datetime):
    ...
