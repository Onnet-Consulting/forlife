# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoField

# special fields - don't declare them in Odoo
DEFAULT_VALUE = {
    'PushDate': 'GETUTCDATE()',
    'Active': 1,
}
INSERT_DEFAULT_VALUE = {**DEFAULT_VALUE}

UPDATE_DEFAULT_VALUE = {**DEFAULT_VALUE}

DELETE_DEFAULT_VALUE = {
    **DEFAULT_VALUE,
    'Active': 0
}


class BravoModel(models.AbstractModel):
    _name = 'bravo.model'
    _inherit = ['mssql.server']

    def get_bravo_values(self):
        bravo_fields = self.fields_bravo_get()
        bravo_column_names = [bfield.bravo_name for bfield in bravo_fields]
        values = []
        for record in self:
            value = {}
            for bfield in bravo_fields:
                value.update(bfield.compute_value(record))
            values.append(value)
        return bravo_column_names, values

    def get_insert_sql(self):
        # FIXME: insert into have limited the number of records to 1000 each time insert
        # TODO: try bulk insert (https://learn.microsoft.com/en-us/sql/odbc/reference/syntax/sqlbulkoperations-function?view=sql-server-ver16)
        column_names, values = self.get_bravo_values()

        if not values:
            return False
        insert_table = self._bravo_table
        params = []
        insert_column_names = column_names.copy()
        single_record_values_placeholder = ['?'] * len(column_names)

        for rec_value in values:
            for fname in column_names:
                params.append(rec_value.get(fname))

        for fname, fvalue in INSERT_DEFAULT_VALUE.items():
            insert_column_names.append(fname)
            single_record_values_placeholder.append(str(fvalue))

        single_record_values_placeholder = "(" + ','.join(single_record_values_placeholder) + ")"
        insert_values_placholder = ','.join([single_record_values_placeholder] * len(values))
        insert_column_names = "(" + ','.join(insert_column_names) + ")"

        query = f"""
        INSERT INTO {insert_table} 
        {insert_column_names}
        VALUES {insert_values_placholder}
        """

        return query, params

    def get_update_sql(self):
        values = self.get_bravo_values()

    def get_delete_sql(self):
        values = self.get_bravo_values(active=False)

    @api.model
    def fields_bravo_get(self):
        res = []
        for bfield in self._fields.values():
            if not issubclass(type(bfield), BravoField):
                continue
            res.append(bfield)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(BravoModel, self).create(vals_list)
        query, params = res.get_insert_sql()
        self.execute(query, params)
        return res
