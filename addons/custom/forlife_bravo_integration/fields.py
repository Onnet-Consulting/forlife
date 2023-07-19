# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.fields import Default
from odoo.tools.float_utils import float_round
from odoo.addons.forlife_base.models.res_utility import convert_localize_datetime
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
    odoo_depend_fields = False  # use this attribute to decide if a computed field be updated

    _description_bravo_name = property(attrgetter('bravo_name'))
    _description_odoo_name = property(attrgetter('odoo_name'))
    _description_identity = property(attrgetter('identity'))

    def __int__(self, bravo_name=Default, bravo_default=bravo_default, odoo_name=Default, identity=Default,
                odoo_depend_fields=Default, **kwargs):
        super(BravoField, self).__int__(bravo_name=bravo_name, bravo_default=bravo_default,
                                        odoo_name=odoo_name, identity=identity,
                                        odoo_depend_fields=odoo_depend_fields, **kwargs)

    def compute_value(self, record):
        if self.bravo_default is not None:
            value = self.bravo_default
        else:
            value = record[self.odoo_name] if self.odoo_name else None
        return {self.bravo_name: value or NONE_VALUE}

    def compute_update_value(self, value, model=Default):
        if self.bravo_default is not None:
            value = self.bravo_default
        else:
            if len(model) > 1:
                model = model[0]
            value = model[self.odoo_name]
        return {self.bravo_name: value or NONE_VALUE}


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
    DEFAULT_BRAVO_TZ = 'Asia/Ho_Chi_Minh'
    bravo_tz = DEFAULT_BRAVO_TZ

    _description_bravo_tz = property(attrgetter('bravo_tz'))

    def __int__(self, bravo_tz=DEFAULT_BRAVO_TZ, **kwargs):
        super(BravoField, self).__int__(bravo_tz=bravo_tz, **kwargs)

    def compute_value(self, record):
        res = super().compute_value(record)
        key, value = res.popitem()
        if not value:
            return {key: value}
        value = convert_localize_datetime(value, tz=self.bravo_tz)
        return {key: value}

    def compute_update_value(self, value, model=Default):
        res = super().compute_update_value(value, model=model)
        if not res:
            return False
        key, value = res.popitem()
        value = convert_localize_datetime(value, tz=self.bravo_tz)
        return {key: value}


class BravoMany2oneField(BravoField, fields.Many2one):
    field_detail = None

    def __int__(self, field_detail=Default, **kwargs):
        super(BravoField, self).__int__(field_detail=field_detail, **kwargs)

    def compute_value(self, record):
        if not self.field_detail or not self.odoo_name:
            return {}
        field_value = record[self.odoo_name]
        for field_name in self.field_detail.split('.'):
            if not field_value:
                break
            field_value = field_value[field_name]
        return {self.bravo_name: field_value or NONE_VALUE}

    def compute_update_value(self, value, model=Default):
        res = super(BravoMany2oneField, self).compute_update_value(value, model=model)
        if not res:
            return res
        key, value = res.popitem()
        if hasattr(value, '_name'):  # already an instance
            field_value = value
        else:
            field_value = model.env[self.comodel_name].browse(value)
        for field_name in self.field_detail.split('.'):
            if not field_value:
                break
            field_value = field_value[field_name]
        return {key: field_value or NONE_VALUE}


class BravoSelectionField(BravoField, fields.Selection):
    mapping_selection = None
    selection = [(1, 1)]

    def __int__(self, mapping_selection=Default, **kwargs):
        super(BravoField, self).__int__(mapping_selection=mapping_selection, **kwargs)

    def compute_value(self, record):
        res = super(BravoSelectionField, self).compute_value(record)
        key, value = res.popitem()
        return {key: self.mapping_selection.get(value) or NONE_VALUE}

    def compute_update_value(self, value, model=Default):
        res = super(BravoSelectionField, self).compute_update_value(value, model=model)
        if not res:
            return res
        key, value = res.popitem()
        field_value = self.mapping_selection.get(value)
        return {key: field_value or NONE_VALUE}


class BravoHeaderField(BravoField, fields.Many2one):
    header_fields = None

    def __init__(self, header_fields=Default, **kwargs):
        super(BravoHeaderField, self).__init__(header_fields=header_fields, **kwargs)
