# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoField


class BravoModelCore(models.AbstractModel):
    _name = 'bravo.model.core'
    _inherit = ['mssql.server']
    _description = 'Bravo Model Core'
    _bravo_table = 'BravoTable'

    @api.model
    def bravo_get_table(self):
        return self._bravo_table

    @api.model
    def bravo_get_filter_domain(self):
        """Get domain to filter records before execute any action"""
        return []

    def bravo_filter_records(self):
        filter_domain = self.bravo_get_filter_domain()
        if not filter_domain:
            return self
        return self.filtered_domain(filter_domain)

    @api.model
    def bravo_fields_get(self, allfields=None):
        res = []
        for bfield in self._fields.values():
            if not issubclass(type(bfield), BravoField) or not hasattr(bfield, "bravo_name"):
                continue
            if allfields and bfield.odoo_name not in allfields:
                continue
            res.append(bfield)
        return res

    @api.model
    def bravo_identity_fields_get(self):
        bravo_fields = self.bravo_fields_get()
        return list(filter(lambda bfield: bfield.identity, bravo_fields))

    def bravo_get_identity_key_values(self):
        values = []
        records = self.bravo_filter_records()
        identity_fields = self.bravo_identity_fields_get()
        for record in records:
            value = {}
            for bfield in identity_fields:
                value.update(bfield.compute_value(record))
            if not value:
                continue
            values.append(value)
        return values


class BravoModelInsertAction(models.AbstractModel):
    _name = 'bravo.model.insert.action'
    _inherit = ['bravo.model.core']
    _description = 'Bravo Model Insert Action'

    @api.model
    def bravo_get_default_insert_value(self):
        # special fields - don't declare them in Odoo
        return {
            'PushDate': 'GETUTCDATE()',
            'Active': 1,
        }

    def bravo_get_insert_values(self):
        records = self.bravo_filter_records()
        bravo_fields = self.bravo_fields_get()
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

    def bravo_get_insert_sql(self):
        column_names, values = self.bravo_get_insert_values()
        queries = []

        if not values:
            return False
        insert_table = self.bravo_get_table()
        params = []
        insert_column_names = column_names.copy()
        single_record_values_placeholder = ['?'] * len(column_names)

        for rec_value in values:
            for fname in column_names:
                params.append(rec_value.get(fname))

        insert_default_value = self.bravo_get_default_insert_value()
        for fname, fvalue in insert_default_value.items():
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
            actual_num_row_per_request = len(sub_params) // num_param_per_row
            if actual_num_row_per_request <= 0:
                break
            insert_values_placeholder = ','.join([single_record_values_placeholder] * actual_num_row_per_request)
            sub_query = f"""
            INSERT INTO {insert_table} 
            {insert_column_names}
            VALUES {insert_values_placeholder}
            """
            queries.append((sub_query, sub_params))
            offset += num_param_per_row * actual_num_row_per_request

        return queries

    def bravo_insert(self):
        queries = self.bravo_get_insert_sql()
        if queries:
            self._execute_many(queries)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        # FIXME: push below function to job queue
        res.sudo().bravo_insert()
        return res


class BravoModelUpdateAction(models.AbstractModel):
    _name = 'bravo.model.update.action'
    _inherit = ['bravo.model.core']
    _description = 'Bravo Model Update Action'

    @api.model
    def bravo_get_default_update_value(self):
        # special fields - don't declare them in Odoo
        return {
            'PushDate': 'GETUTCDATE()',
            'Active': 1,
        }

    def bravo_get_update_values(self, values):
        updated_fields = list(values.keys())
        bravo_fields = self.bravo_fields_get(allfields=updated_fields)
        bravo_values = {}

        for bfield in bravo_fields:
            bvalue = bfield.compute_update_value(values, self)
            if bvalue:
                bravo_values.update(bvalue)
        return bravo_values

    def bravo_get_update_sql(self, values):
        """
        @param dict values: odoo updated value (or bravo updated value)
        """
        updated_values = self.bravo_get_update_values(values)
        identity_key_values = self.bravo_get_identity_key_values()

        if not updated_values or not identity_key_values:
            return False
        update_table_name = self.bravo_get_table()

        set_query_params = []
        set_query_placeholder = []
        for key, value in updated_values.items():
            set_query_placeholder.append(f"{key}=?")
            set_query_params.append(value)
        update_default_value = self.bravo_get_default_update_value()
        for key, value in update_default_value.items():
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
            actual_num_row_per_request = len(sub_where_params) // num_param_per_where_condition
            if actual_num_row_per_request <= 0:
                break
            where_query_placeholder = " or ".join([single_where_value] * actual_num_row_per_request)
            query = f"""
                UPDATE {update_table_name}
                SET {set_query_placeholder}
                WHERE {where_query_placeholder}
            """
            queries.append((query, set_query_params + sub_where_params))
            offset += num_param_per_where_condition * actual_num_row_per_request

        return queries

    def bravo_update(self, values):
        queries = self.bravo_get_update_sql(values)
        if queries:
            self._execute_many(queries)
        return True

    def write(self, vals):
        res = super().write(vals)
        # FIXME: push below function to job queue
        self.sudo().bravo_update(vals)
        return res


class BravoModelDeleteAction(models.AbstractModel):
    _name = 'bravo.model.delete.action'
    _inherit = ['bravo.model.core']
    _description = 'Bravo Model Delete Action'

    @api.model
    def bravo_get_default_delete_values(self):
        # special fields - don't declare them in Odoo
        return {
            'PushDate': 'GETUTCDATE()',
            'Active': 0,
        }

    def bravo_get_delete_sql(self):
        identity_key_values = self.bravo_get_identity_key_values()

        if not identity_key_values:
            return False
        update_table_name = self.bravo_get_table()

        set_query_params = []
        set_query_placeholder = []
        delete_default_value = self.bravo_get_default_delete_values()
        for key, value in delete_default_value.items():
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
            actual_num_row_per_request = len(sub_where_params) // num_param_per_where_condition
            if actual_num_row_per_request <= 0:
                break
            where_query_placeholder = " or ".join([single_where_value] * actual_num_row_per_request)
            query = f"""
                UPDATE {update_table_name}
                SET {set_query_placeholder}
                WHERE {where_query_placeholder}
            """
            queries.append((query, set_query_params + sub_where_params))
            offset += num_param_per_where_condition * actual_num_row_per_request

        return queries

    def bravo_delete(self, queries):
        if queries:
            self._execute_many(queries)
        return True

    def unlink(self):
        # need to extract query and params before records be deleted in Odoo
        queries = self.sudo().bravo_get_delete_sql()
        res = super().unlink()
        # FIXME: push below function to job queue
        self.sudo().bravo_delete(queries)
        return res


class BravoModel(models.AbstractModel):
    _name = 'bravo.model'
    _inherit = ['bravo.model.insert.action', 'bravo.model.update.action', 'bravo.model.delete.action']
    _description = 'Bravo Model'

    # ==========================================
    def get_existing_records_before_insert_sql(self):
        identity_key_values = self.get_bravo_identity_key_values()
        if not identity_key_values:
            return False

        identity_keys = self.fields_bravo_identity_get()
        identity_key_names = [bfield.bravo_name for bfield in identity_keys]
        bravo_table = self.get_bravo_table()
        single_where_query_placeholder = [f"{ikey}=?" for ikey in identity_key_names]
        single_where_query_placeholder = f"({' and '.join(single_where_query_placeholder)})"
        where_query_params = []

        for value in identity_key_values:
            where_query_params.extend([value.get(ikey) for ikey in identity_key_names if value.get(ikey)])

        num_param_per_where_condition = max(len(identity_key_names), 1)
        num_row_per_request = 2000 // num_param_per_where_condition
        offset = 0
        queries = []

        while True:
            sub_where_params = where_query_params[offset: num_param_per_where_condition * num_row_per_request + offset]
            actual_num_row_per_request = len(sub_where_params) // num_param_per_where_condition
            if actual_num_row_per_request <= 0:
                break

            where_query_placeholder = " or ".join([single_where_query_placeholder] * actual_num_row_per_request)
            query = f"""
                SELECT {','.join(identity_key_names)} 
                FROM {bravo_table}
                WHERE {where_query_placeholder}
            """
            queries.append((query, sub_where_params))
            offset += num_param_per_where_condition * actual_num_row_per_request

        return queries

    def separate_records_by_identity_values(self, identity_values):
        existing_records = self.env[self._name]
        newly_records = self.env[self._name]
        for rec in self:
            record_identity_value = rec.get_bravo_identity_key_values()
            if record_identity_value and record_identity_value[0] in identity_values:
                existing_records += rec
            else:
                newly_records += rec
        return existing_records, newly_records

    def separate_records_before_insert(self):
        queries = self.get_existing_records_before_insert_sql()
        identity_values = []
        if queries:
            for data in self._execute_many_read(queries):
                identity_values.extend([dict(zip(['Code'], row)) for row in data])
        return self.separate_records_by_identity_values(identity_values)

    def insert_into_bravo_db_with_check_existing(self):
        existing_records, newly_records = self.separate_records_before_insert()
        # update records existed
        # insert remain records (don't exist in Bravo yet)
        pass
