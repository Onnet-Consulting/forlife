# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re

CONTEXT_CATEGORY_KEY = 'bravo_product_category_level'
CONTEXT_CATEGORY_ACCOUNT_KEY = 'bravo_product_category_need_accounts'


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'bravo.model']

    @api.model
    def bravo_get_table(self, **kwargs):
        product_category_level = kwargs.get(CONTEXT_CATEGORY_KEY)
        product_category_need_accounts = kwargs.get(CONTEXT_CATEGORY_ACCOUNT_KEY)
        bravo_table = self._bravo_table
        if product_category_need_accounts:
            bravo_table = 'B20ItemGroup'
        elif product_category_level:
            if product_category_level == 4:
                bravo_table = 'B20Structure'
            elif product_category_level == 3:
                bravo_table = 'B20ItemLine'
            elif product_category_level == 2:
                bravo_table = 'B20CommodityGroup'
            elif product_category_level == 1:
                bravo_table = 'B20Brand'
        if bravo_table == 'BravoTable':
            raise ValidationError(_('%s is not a valid Bravo table name' % bravo_table))
        return bravo_table

    def bravo_get_identity_key_values(self):
        records = self.bravo_filter_records()
        res = []
        for record in records:
            value = {'Code': record.category_code}
            res.append(value)
        return res

    def bravo_get_identity_key_names(self):
        return ['Code']

    def bravo_get_record_values(self, to_update=False):
        bravo_column_names = [
            "Code", "Name"
        ]
        if not self:
            if to_update:
                return []
            return bravo_column_names, []
        values = []
        for record in self:
            value = {"Name": record.name}
            if not to_update:
                value.update({
                    "Code": record.category_code
                })
            values.append(value)

        if to_update:
            return values
        return bravo_column_names, values

    def bravo_get_update_value_for_existing_record(self):
        values = self.bravo_get_update_values(True)
        if values:
            return values[0] if type(values) is list else values
        return {}

    def bravo_get_insert_values(self, **kwargs):
        return self.bravo_get_record_values()

    def bravo_get_update_values(self, values):
        res = self.bravo_get_record_values(to_update=True)
        if not res:
            return {}
        return res[0]

    def bravo_filter_record_by_level(self, level):
        return self.filtered(lambda rec: len(re.findall('/', rec.parent_path)) == level)

    def bravo_filter_record_need_send_account(self):
        return self.filtered(lambda rec: rec.child_id)

    def bravo_get_inset_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            insert_sql = records.bravo_get_insert_sql(**{CONTEXT_CATEGORY_KEY: level})
            queries.extend(insert_sql)
        return queries

    def bravo_get_insert_sql(self, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_KEY):
            return super().bravo_get_insert_sql(**kwargs)
        return self.bravo_get_inset_sql_all_level()

    def bravo_get_update_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            update_sql = records.bravo_get_update_sql(None, **{CONTEXT_CATEGORY_KEY: level})
            # category_with_account_update_sql = records.bravo_get_update_sql(None, **{CONTEXT_CATEGORY_ACCOUNT_KEY: True})
            queries.extend(update_sql)
            # queries.extend(category_with_account_update_sql)
        return queries

    def bravo_get_update_sql(self, values=None, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_KEY):
            return super().bravo_get_update_sql(values, **kwargs)
        return self.bravo_get_update_sql_all_level()

    def bravo_get_insert_with_check_existing_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            update_sql = records.bravo_get_insert_with_check_existing_sql(**{CONTEXT_CATEGORY_KEY: level})
            queries.extend(update_sql)
        return queries

    def bravo_get_insert_with_check_existing_sql(self, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_KEY):
            return super().bravo_get_insert_with_check_existing_sql(**kwargs)
        return self.bravo_get_insert_with_check_existing_sql_all_level()

    def bravo_get_delete_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            delete_sql = records.bravo_get_delete_sql(**{CONTEXT_CATEGORY_KEY: level})
            queries.extend(delete_sql)
        return queries

    def bravo_get_delete_sql(self, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_KEY):
            return super().bravo_get_delete_sql(**kwargs)
        return self.bravo_get_delete_sql_all_level()
