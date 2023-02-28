# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.fields import Default
from odoo.tools.float_utils import float_round
from datetime import date, datetime, time
from operator import attrgetter



class BravoModel(models.AbstractModel):
    _name = 'bravo.model'

    def generate_fields(self):
        pass


class BravoField(fields.Field):
    bravo_name = None
    odoo_name = None
    store = False

    def __int__(self, string=Default,bravo_name=Default, odoo_name=Default, **kwargs):
        super(BravoField, self).__int__(string=string,bravo_name=bravo_name, odoo_name=odoo_name, **kwargs)

    def convert_value(self, value):
        return value


class BravoCharField(fields.Field):
    type = 'bravo_char'
    column_type = ('varchar', 'varchar')

    bravo_name = None
    odoo_name = None
    store = False

    def __init__(self, bravo_name=Default, odoo_name=Default, **kwargs):
        super(BravoCharField, self).__init__(bravo_name=bravo_name, odoo_name=odoo_name, **kwargs)

    _description_bravo_name = property(attrgetter('bravo_name'))
    _description_odoo_name = property(attrgetter('odoo_name'))

    def convert_to_column(self, value, record, values=None, validate=True):
        return value

    def convert_to_cache(self, value, record, validate=True):
        return value

    def convert_to_record(self, value, record):
        return value

    def convert_to_read(self, value, record, use_name_get=True):
        return value

    def convert_to_write(self, value, record):
        return value


class BravoIntegerField(BravoField):
    def convert_value(self, value):
        return int(value or 0)


class BravoDecimalField(BravoField):
    precision_digits = None

    def convert_value(self, value):
        value = float(value or 0.0)
        precision_digits = self.precision_digits or 0
        return float_round(value, precision_digits)


class BravoDateField(BravoField):
    date_format = 'YYYY-MM-DD'

    def convert_value(self, value):
        if not value:
            return None
        return datetime.strftime(value, self.date_format)
