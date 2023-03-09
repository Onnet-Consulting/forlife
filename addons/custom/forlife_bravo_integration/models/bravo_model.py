# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoField, BravoCharField, BravoDatetimeField, BravoDateField, \
    BravoMany2oneField, BravoIntegerField, BravoDecimalField
from odoo.exceptions import ValidationError

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

    @api.model
    def get_bravo_filter_domain(self):
        return []

    def filter_bravo_records(self):
        return self.filtered_domain(self.get_bravo_filter_domain())

    def get_bravo_insert_values(self):
        records = self.filter_bravo_records()
        bravo_fields = self.fields_bravo_get()
        bravo_column_names = [bfield.bravo_name for bfield in bravo_fields]
        values = []
        for record in records:
            value = {}
            for bfield in bravo_fields:
                value.update(bfield.compute_value(record))
            if not value:
                continue
            values.append(value)
        return bravo_column_names, values

    def get_bravo_update_values(self, values):
        updated_fields = list(values.keys())
        bravo_fields = self.fields_bravo_get(allfields=updated_fields)
        bravo_values = {}

        for bfield in bravo_fields:
            bvalue = bfield.compute_update_value(values, self)
            if bvalue:
                bravo_values.update(bvalue)
        return bravo_values

    def get_bravo_identity_key_values(self):
        values = []
        records = self.filter_bravo_records()
        identity_fields = self.fields_bravo_identity_get()
        for record in records:
            value = {}
            for bfield in identity_fields:
                value.update(bfield.compute_value(record))
            if not value:
                continue
            values.append(value)
        return values

    def get_insert_sql(self):
        column_names, values = self.get_bravo_insert_values()
        queries = []

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
        insert_column_names = "(" + ','.join(insert_column_names) + ")"

        # LIMITATION params per request is 2100 -> so 2000 params per request is a reasonable number
        num_param_per_row = len(column_names)
        num_row_per_request = 2000 // num_param_per_row
        offset = 0
        while True:
            sub_params = params[offset: num_row_per_request * num_param_per_row + offset]
            actual_num_row = len(sub_params) // num_param_per_row
            if actual_num_row <= 0:
                break
            insert_values_placholder = ','.join([single_record_values_placeholder] * actual_num_row)
            sub_query = f"""
            INSERT INTO {insert_table} 
            {insert_column_names}
            VALUES {insert_values_placholder}
            """
            queries.append((sub_query, sub_params))
            offset += num_row_per_request * num_param_per_row

        return queries

    def get_update_sql(self, values):
        """
        @param dict values: odoo updated value (or bravo updated value)
        """
        updated_values = self.get_bravo_update_values(values)
        identity_key_values = self.get_bravo_identity_key_values()

        if not updated_values or not identity_key_values:
            return False
        update_table_name = self._bravo_table

        set_query_params = []
        set_query_placeholder = []
        for key, value in updated_values.items():
            set_query_placeholder.append(f"{key}=?")
            set_query_params.append(value)
        for key, value in UPDATE_DEFAULT_VALUE.items():
            set_query_placeholder.append(f"{key}={value}")
        set_query_placeholder = ','.join(set_query_placeholder)

        single_where_value = []
        for upkey, upvalue in identity_key_values[0].items():
            single_where_value.append(f"{upkey} = ?")
        single_where_value = "(" + ' and '.join(single_where_value) + ")"

        where_params = []
        for value in identity_key_values:
            for ivalue in value.values():
                where_params.append(ivalue)

        num_param_per_where_condition = max(len(identity_key_values[0].keys()), 1)
        num_row_per_request = 2000 // num_param_per_where_condition
        offset = 0
        queries = []

        while True:
            sub_where_params = where_params[offset: num_param_per_where_condition * num_row_per_request + offset]
            actual_num_row = len(sub_where_params) // num_param_per_where_condition
            if actual_num_row <= 0:
                break
            where_query_placholder = " or ".join([single_where_value] * actual_num_row)
            query = f"""
                UPDATE {update_table_name}
                SET {set_query_placeholder}
                WHERE {where_query_placholder}
            """
            queries.append((query, set_query_params + sub_where_params))
            offset += num_param_per_where_condition * num_row_per_request

        return queries

    def get_delete_sql(self):
        identity_key_values = self.get_bravo_identity_key_values()

        if not identity_key_values:
            return False
        update_table_name = self._bravo_table

        set_query_params = []
        set_query_placeholder = []
        for key, value in DELETE_DEFAULT_VALUE.items():
            set_query_placeholder.append(f"{key}={value}")
        set_query_placeholder = ','.join(set_query_placeholder)

        single_where_value = []
        for upkey, upvalue in identity_key_values[0].items():
            single_where_value.append(f"{upkey} = ?")
        single_where_value = "(" + ' and '.join(single_where_value) + ")"

        where_params = []
        for value in identity_key_values:
            for ivalue in value.values():
                where_params.append(ivalue)

        num_param_per_where_condition = max(len(identity_key_values[0].keys()), 1)
        num_row_per_request = 2000 // num_param_per_where_condition
        offset = 0
        queries = []

        while True:
            sub_where_params = where_params[offset: num_param_per_where_condition * num_row_per_request + offset]
            actual_num_row = len(sub_where_params) // num_param_per_where_condition
            if actual_num_row <= 0:
                break
            where_query_placholder = " or ".join([single_where_value] * actual_num_row)
            query = f"""
                UPDATE {update_table_name}
                SET {set_query_placeholder}
                WHERE {where_query_placholder}
            """
            queries.append((query, set_query_params + sub_where_params))
            offset += num_param_per_where_condition * num_row_per_request

        return queries

    @api.model
    def fields_bravo_get(self, allfields=None):
        res = []
        for bfield in self._fields.values():
            if not issubclass(type(bfield), BravoField) or not hasattr(bfield, "bravo_name"):
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
        queries = self.get_insert_sql()
        if queries:
            self._execute_many(queries)
        return True

    def update_bravo_db(self, values):
        queries = self.get_update_sql(values)
        if queries:
            self._execute_many(queries)
        return True

    def delete_bravo_data_db(self, queries):
        if queries:
            self._execute_many(queries)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        res = super(BravoModel, self).create(vals_list)
        # FIXME: push below function to job queue
        res.sudo().insert_into_bravo_db()
        return res

    def write(self, vals):
        res = super(BravoModel, self).write(vals)
        # FIXME: push below function to job queue
        self.sudo().update_bravo_db(vals)
        return res

    def unlink(self):
        # need to extract query and params before records be deleted in Odoo
        queries = self.sudo().get_delete_sql()
        res = super(BravoModel, self).unlink()
        # FIXME: push below function to job queue
        self.sudo().delete_bravo_data_db(queries)
        return res


class BravoHeaderModel(models.AbstractModel):
    _name = 'bravo.header.model'
    _inherit = 'bravo.model'
    _bravo_update_table = 'B30UpdateData'

    def get_current_record_value_to_update(self):
        self.ensure_one()
        bravo_columns = ['BranchCode', 'DocNo', 'DocDate', 'Stt']
        current_record_value = {}
        bravo_fields = self.fields_bravo_get()
        bravo_field_mapping = {bfield.bravo_name: bfield for bfield in bravo_fields}
        for bfield in bravo_fields:
            if bfield.bravo_name in bravo_columns:
                current_record_value.update(bfield.compute_value(self))
        if not current_record_value:
            raise ValidationError("No value for insert to %s table" % self._bravo_update_table)
        return bravo_field_mapping, current_record_value

    def get_record_updated_value_to_update(self, values):
        UPDATE_SPECIAL_VALUES = {
            'UpdateType': '1',
            'PushDate': 'GETUTCDATE()',
        }
        bravo_field_mapping, current_record_value = self.get_current_record_value_to_update()
        bravo_updated_value = self.get_bravo_update_values(values)
        queries = []
        for key, value in bravo_updated_value.items():
            bfield = bravo_field_mapping.get(key)
            if not bfield:
                continue
            record_value = current_record_value.copy()
            old_value = bfield.compute_value(self)
            record_value.update({
                'ColumnName': key,
                'OldValue': old_value[key] if old_value else None,
                'NewValue': value
            })
            record_value.update(UPDATE_SPECIAL_VALUES)
            queries.append(record_value)
        return queries

    def write(self, vals):
        record_values = self.sudo().get_record_updated_value_to_update(vals)
        # TODO: generate insert sql to table self._bravo_update_table from record_values here
        res = super(BravoModel, self).write(vals)
        # FIXME: push below function to job queue

        return res

    def insert_into_bravo_update_table(self):
        pass

    def insert_into_bravo_db(self):
        pass

    def update_bravo_db(self):
        pass

    def delete_bravo_data_db(self, values):
        pass


class BravoLineModel(models.AbstractModel):
    _name = 'bravo.line.model'
    _inherit = 'bravo.model'
    _bravo_update_table = 'B30UpdateData'

    def get_bravo_header_insert_values(self):
        # get insert values of header table here
        header_field = self._bravo_header_field
        header_record = self.mapped(header_field)
        header_record.ensure_one()
        header_columns, header_values = header_record.get_bravo_insert_values()
        return header_columns, header_values[0]

    def get_bravo_insert_values(self):
        line_columns, line_values = super(BravoLineModel, self).get_bravo_insert_values()
        header_columns, header_value = self.get_bravo_header_insert_values()
        line_columns.extend(header_columns)
        for value in line_values:
            value.update(header_value)
        return line_columns, line_values

    def get_bravo_update_values(self, values):
        ...

    def get_update_sql(self, values):
        update_table = self._bravo_update_table

