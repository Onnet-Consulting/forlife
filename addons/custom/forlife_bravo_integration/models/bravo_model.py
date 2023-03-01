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

    def get_bravo_insert_values(self):
        bravo_fields = self.fields_bravo_get()
        bravo_column_names = [bfield.bravo_name for bfield in bravo_fields]
        values = []
        for record in self:
            value = {}
            for bfield in bravo_fields:
                value.update(bfield.compute_value(record))
            values.append(value)
        return bravo_column_names, values

    def get_bravo_update_values(self, values):
        updated_fields = list(values.keys())
        bravo_fields = self.fields_bravo_get(allfields=updated_fields)
        bravo_odoo_mapping = {bfield.odoo_name: bfield.bravo_name for bfield in bravo_fields}
        bravo_values = {}

        for odoo_name, odoo_value in values.items():
            bravo_values[bravo_odoo_mapping[odoo_name]] = odoo_value
        return bravo_values

    def get_bravo_update_key_values(self):
        values = []
        identity_fields = self.fields_bravo_identity_get()
        for record in self:
            value = {}
            for bfield in identity_fields:
                value.update(bfield.compute_value(record))
            values.append(value)
        return values

    def get_insert_sql(self):
        # FIXME: insert into have limited the number of records to 1000 each time insert
        # TODO: try bulk insert (https://learn.microsoft.com/en-us/sql/odbc/reference/syntax/sqlbulkoperations-function?view=sql-server-ver16)
        column_names, values = self.get_bravo_insert_values()

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

    def get_update_sql(self, values):
        updated_values = self.get_bravo_update_values(values)
        updated_key_values = self.get_bravo_update_key_values()
        params = []
        if not updated_values:
            return False
        update_table_name = self._bravo_table

        set_query_value = []
        for key, value in updated_values.items():
            set_query_value.append(f"{key}=?")
            params.append(value)
        for key, value in INSERT_DEFAULT_VALUE.items():
            set_query_value.append(f"{key}={value}")
        set_query_value = ','.join(set_query_value)

        where_query_value = []
        for value in updated_key_values:
            single_update = []
            for upkey, upvalue in value.items():
                single_update.append(f"{upkey} = ?")
                params.append(upvalue)
            single_update = "(" + ' and '.join(single_update) + ")"
            where_query_value.append(single_update)
        where_query_value = ' or '.join(where_query_value)

        query = f"""
            UPDATE {update_table_name}
            SET {set_query_value}
            WHERE {where_query_value}
        """
        return query, params

    def get_delete_sql(self):
        values = self.get_bravo_insert_values(active=False)

    @api.model
    def fields_bravo_get(self, allfields=None):
        res = []
        for bfield in self._fields.values():
            if not issubclass(type(bfield), BravoField) \
                    or not hasattr(bfield, "odoo_name") or not hasattr(bfield, "bravo_name"):
                continue
            if allfields and bfield.odoo_name not in allfields:
                continue
            res.append(bfield)
        return res

    @api.model
    def fields_bravo_identity_get(self):
        bravo_fields = self.fields_bravo_get()
        return list(filter(lambda bfield: bfield.identity, bravo_fields))

    def insert_into_bravo_db(self):
        query, params = self.get_insert_sql()
        self._execute(query, params)
        return True

    def update_bravo_db(self, values):
        query, params = self.get_update_sql(values)
        self._execute(query, params)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        res = super(BravoModel, self).create(vals_list)
        # FIXME: push below function to job queue
        res.insert_into_bravo_db()
        return res

    def write(self, vals):
        res = super(BravoModel, self).write(vals)
        self.update_bravo_db(vals)
        return res
