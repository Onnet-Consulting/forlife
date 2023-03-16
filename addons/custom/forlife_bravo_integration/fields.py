# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.fields import Default
from odoo.tools.float_utils import float_round
from datetime import date, datetime, time
from operator import attrgetter

MSSQL_DATE_FORMAT = '%Y-%m-%d'
MSSQL_TIME_FORMAT = '%H:%M:%S'

NONE_VALUE = None


class BravoField(fields.Field):
    bravo_name = None
    bravo_default = None
    odoo_name = None
    identity = False  # fields with identity = True use to indentify which record to update or delete
    store = False  # don't save to Odoo DB
    groups = "base.group_no_one"  # prevent normal user read this field type

    _description_bravo_name = property(attrgetter('bravo_name'))
    _description_odoo_name = property(attrgetter('odoo_name'))
    _description_identity = property(attrgetter('identity'))

    def __int__(self, bravo_name=Default, bravo_default=bravo_default, odoo_name=Default, identity=Default, **kwargs):
        super(BravoField, self).__int__(bravo_name=bravo_name, bravo_default=bravo_default,
                                        odoo_name=odoo_name, identity=identity, **kwargs)

    def compute_value(self, record):
        if self.bravo_default is not None:
            value = self.bravo_default
        else:
            value = record[self.odoo_name]
        return {self.bravo_name: value or NONE_VALUE}

    def compute_update_value(self, value, model=Default):
        odoo_name = self.odoo_name
        if odoo_name not in value:
            return NONE_VALUE
        return {self.bravo_name: value.get(odoo_name) or NONE_VALUE}


class BravoCharField(BravoField, fields.Char):
    ...


class BravoIntegerField(BravoField, fields.Integer):
    def compute_value(self, record):
        res = super(BravoIntegerField, self).compute_value(record)
        key, value = res.popitem()
        return {key: value or 0}

    def compute_update_value(self, value, model=Default):
        res = super(BravoIntegerField, self).compute_update_value(value, model=model)
        if not res:
            return 0
        key, value = res.popitem()
        return {key: value or 0}


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

    def compute_update_value(self, value, model=Default):
        res = super(BravoDecimalField, self).compute_update_value(value, model=model)
        if not res:
            return 0
        key, value = res.popitem()
        return {key: value or 0}


class BravoDateField(BravoField, fields.Date):
    ...


class BravoDatetimeField(BravoField, fields.Datetime):
    ...


class BravoMany2oneField(BravoField, fields.Many2one):
    field_detail = None

    def __int__(self, field_detail=Default, **kwargs):
        super(BravoField, self).__int__(field_detail=field_detail, **kwargs)

    def compute_value(self, record):
        field_value = record[self.odoo_name]
        for field_name in self.field_detail.split('.'):
            if not field_value:
                break
            field_value = field_value[field_name]
        return {self.bravo_name: field_value or NONE_VALUE}

    def compute_update_value(self, value, model=Default):
        res = super(BravoMany2oneField, self).compute_update_value(value)
        if not res:
            return res
        key, value = res.popitem()
        field_value = model.env[self.comodel_name].browse(value)
        for field_name in self.field_detail.split('.'):
            if not field_value:
                break
            field_value = field_value[field_name]
        return {key: field_value or NONE_VALUE}


class BravoHeaderField(BravoField, fields.Many2one):
    header_fields = None

    def __init__(self, header_fields=Default, **kwargs):
        super(BravoHeaderField, self).__init__(header_fields=header_fields, **kwargs)
