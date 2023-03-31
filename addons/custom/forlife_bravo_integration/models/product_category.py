# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'bravo.model']

    @api.model
    def bravo_get_table_by_level(self, level):
        if level == 4:
            bravo_table = 'B20Structure'
        elif level == 3:
            bravo_table = 'B20ItemLine'
        elif level == 2:
            bravo_table = 'B20ItemGroup'
        else:
            bravo_table = 'B20Brand'
        return bravo_table

    def bravo_get_values_by_level(self, level):
        records = self.bravo_filter_records()
        bravo_table = self.bravo_get_table_by_level(level)
        bravo_column_names = [
            "Code", "Name",
            "ItemAccount", "COGSAccount", "SalesAccount",
            "ItemAccount1", "COGSAccount1", "SalesAccount1",
            "ItemAccount2", "COGSAccount2", "SalesAccount2",
            "ItemAccount3", "COGSAccount3", "SalesAccount3",
        ]
        records = records.filtered(lambda rec: len(re.findall('/', rec.parent_path)) == level)
        if not records:
            return bravo_table, bravo_column_names, []
        company_codes = ['1100', '1200', '1300', '1400']
        companies = self.env['res.company'].sudo().search([('code', 'in', company_codes)])
        company_by_code = {c.code: c for c in companies}
        missing_company_codes = set(company_codes) - set(company_by_code.keys())
        if missing_company_codes:
            raise ValidationError(_("Missing company codes: %r") % list(missing_company_codes))

        values = []
        for record in records:
            value = {"Code": record.category_code, "Name": record.name}
            record_1200 = record.with_company(company_by_code['1200']).sudo()
            value.update({
                "ItemAccount": record_1200.property_stock_valuation_account_id.code,
                "COGSAccount": record_1200.property_account_expense_categ_id.code,
                "SalesAccount": record_1200.property_account_income_categ_id.code,
            })
            record_1300 = record.with_company(company_by_code['1300']).sudo()
            value.update({
                "ItemAccount1": record_1300.property_stock_valuation_account_id.code,
                "COGSAccount1": record_1300.property_account_expense_categ_id.code,
                "SalesAccount1": record_1300.property_account_income_categ_id.code,
            })
            record_1400 = record.with_company(company_by_code['1400']).sudo()
            value.update({
                "ItemAccount2": record_1400.property_stock_valuation_account_id.code,
                "COGSAccount2": record_1400.property_account_expense_categ_id.code,
                "SalesAccount2": record_1400.property_account_income_categ_id.code,
            })
            record_1100 = record.with_company(company_by_code['1100']).sudo()
            value.update({
                "ItemAccount3": record_1100.property_stock_valuation_account_id.code,
                "COGSAccount3": record_1100.property_account_expense_categ_id.code,
                "SalesAccount3": record_1100.property_account_income_categ_id.code,
            })
            values.append(value)
        return bravo_table, bravo_column_names, values

    def get_bravo_insert_sql_by_level(self, level):
        bravo_table, column_names, values = self.bravo_get_values_by_level(level)
        queries = []
        if not values:
            return []
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
            actual_num_row = len(sub_params) // num_param_per_row
            if actual_num_row <= 0:
                break
            insert_values_placholder = ','.join([single_record_values_placeholder] * actual_num_row)
            sub_query = f"""
                INSERT INTO {bravo_table} 
                {insert_column_names}
                VALUES {insert_values_placholder}
                """
            queries.append((sub_query, sub_params))
            offset += num_param_per_row * actual_num_row

        return queries

    def bravo_get_insert_sql(self):
        insert_sql_level_1 = self.get_bravo_insert_sql_by_level(1)
        insert_sql_level_2 = self.get_bravo_insert_sql_by_level(2)
        insert_sql_level_3 = self.get_bravo_insert_sql_by_level(3)
        insert_sql_level_4 = self.get_bravo_insert_sql_by_level(4)
        queries = []
        queries.extend(insert_sql_level_1)
        queries.extend(insert_sql_level_2)
        queries.extend(insert_sql_level_3)
        queries.extend(insert_sql_level_4)
        return queries

    def bravo_get_update_sql_by_level(self, level):
        """1 update query -> 1 record instead of multiple records like other models"""
        bravo_table, column_names, values = self.bravo_get_values_by_level(level)
        if not values:
            return []

        queries = []
        for data in values:
            set_query_params = []
            set_query_placeholder = []
            for key, value in data.items():
                if key == 'Code':
                    # don't update Code column, it's really awkward
                    continue
                set_query_placeholder.append(f"{key}=?")
                set_query_params.append(value)
            set_query_placeholder.extend(["PushDate=GETUTCDATE(), Active=1"])
            set_query_placeholder = ','.join(set_query_placeholder)
            where_query_placeholder = 'Code = ?'
            where_query_param = [data.get('Code')]
            query = f"""
                UPDATE {bravo_table}
                SET {set_query_placeholder}
                WHERE {where_query_placeholder}
            """
            queries.append((query, set_query_params + where_query_param))

        return queries

    def bravo_get_delete_sql_by_level(self, level):
        records = self.bravo_filter_records()
        bravo_table = self.bravo_get_table_by_level(level)
        records = records.filtered(lambda rec: len(re.findall('/', rec.parent_path)) == level)
        if not records:
            return []
        identity_key_values = [{'Code': rec.category_code} for rec in records]
        set_query_params = []
        set_query_placeholder = []
        delete_default_value = self.get_delete_default_value()
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
            actual_num_row = len(sub_where_params) // num_param_per_where_condition
            if actual_num_row <= 0:
                break
            where_query_placholder = " or ".join([single_where_value] * actual_num_row)
            query = f"""
                        UPDATE {bravo_table}
                        SET {set_query_placeholder}
                        WHERE {where_query_placholder}
                    """
            queries.append((query, set_query_params + sub_where_params))
            offset += num_param_per_where_condition * actual_num_row

        return queries

    def bravo_get_delete_sql(self):
        delete_sql_level_1 = self.bravo_get_delete_sql_by_level(1)
        delete_sql_level_2 = self.bravo_get_delete_sql_by_level(2)
        delete_sql_level_3 = self.bravo_get_delete_sql_by_level(3)
        delete_sql_level_4 = self.bravo_get_delete_sql_by_level(4)
        queries = []
        queries.extend(delete_sql_level_1)
        queries.extend(delete_sql_level_2)
        queries.extend(delete_sql_level_3)
        queries.extend(delete_sql_level_4)
        return queries

    def bravo_get_update_sql(self, values):
        update_sql_level_1 = self.bravo_get_update_sql_by_level(1)
        update_sql_level_2 = self.bravo_get_update_sql_by_level(2)
        update_sql_level_3 = self.bravo_get_update_sql_by_level(3)
        update_sql_level_4 = self.bravo_get_update_sql_by_level(4)
        queries = []
        queries.extend(update_sql_level_1)
        queries.extend(update_sql_level_2)
        queries.extend(update_sql_level_3)
        queries.extend(update_sql_level_4)
        return queries
