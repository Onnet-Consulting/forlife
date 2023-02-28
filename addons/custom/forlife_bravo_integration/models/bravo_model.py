# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.fields import Default
from odoo.tools.float_utils import float_round
from datetime import date, datetime, time
from operator import attrgetter
from ..fields import BravoField


class BravoModel(models.AbstractModel):
    _name = 'bravo.model'

    def get_bravo_values(self):
        bravo_fields = self.fields_bravo_get()
        res = []
        for record in self:
            value = {}
            for bfield in bravo_fields:
                value.update(bfield.compute_value(record))
            res.append(value)
        return res

    @api.model
    def fields_bravo_get(self):
        res = []
        for field in self._fields.values():
            if field.groups and not self.env.su and not self.user_has_groups(field.groups):
                continue
            if not issubclass(type(field), BravoField):
                continue
            res.append(field)

        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(BravoModel, self).create(vals_list)
        x = res.get_bravo_values()
        return res
