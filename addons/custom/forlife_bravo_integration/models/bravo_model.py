# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoField


class BravoModel(models.AbstractModel):
    _name = 'bravo.model'
    _inherit = ['mssql.server']

    def get_bravo_values(self, active=True):
        bravo_fields = self.fields_bravo_get()
        res = []
        for record in self:
            value = {}
            for bfield in bravo_fields:
                value.update(bfield.compute_value(record))
                value.update({"active": active})
            res.append(value)
        return res

    def get_insert_sql(self):
        # FIXME: insert into have limited the number of records to 1000 each time insert
        values = self.get_bravo_values()
        if not values:
            return False
        field_names = list(values[0].keys())
        params = []
        for rec_value in values:
            for fname in field_names:
                params.append(rec_value.get(fname))

        field_values_placeholder = ','.join(['?']*len(field_names))
        values_placeholder = ','.join([f"({field_values_placeholder})"])
        field_names = ','.join(field_names)
        query = f"""
        INSERT INTO {self._bravo_table} ({field_names})
        VALUES {values_placeholder}
        """
        return query, params

    def get_update_sql(self):
        values = self.get_bravo_values()

    def get_delete_sql(self):
        values = self.get_bravo_values(active=False)

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
        query, params = res.get_insert_sql()
        self.execute(query, params)
        return res
