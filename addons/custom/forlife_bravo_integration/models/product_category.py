# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re

CONTEXT_CATEGORY_KEY = 'product_category_level'


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'bravo.model']

    @api.model
    def bravo_get_table(self):
        product_category_level = self.env.context.get(CONTEXT_CATEGORY_KEY)
        if product_category_level:
            if product_category_level == 4:
                bravo_table = 'B20Structure'
            elif product_category_level == 3:
                bravo_table = 'B20ItemLine'
            elif product_category_level == 2:
                bravo_table = 'B20ItemGroup'
            else:
                bravo_table = 'B20Brand'
            return bravo_table
        else:
            return self._bravo_table

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
            "Code", "Name",
            "ItemAccount", "COGSAccount", "SalesAccount",
            "ItemAccount1", "COGSAccount1", "SalesAccount1",
            "ItemAccount2", "COGSAccount2", "SalesAccount2",
            "ItemAccount3", "COGSAccount3", "SalesAccount3",
        ]
        if not self:
            if to_update:
                return []
            return bravo_column_names, []
        company_codes = ['1100', '1200', '1300', '1400']
        companies = self.env['res.company'].sudo().search([('code', 'in', company_codes)])
        company_by_code = {c.code: c for c in companies}
        missing_company_codes = set(company_codes) - set(company_by_code.keys())
        if missing_company_codes:
            raise ValidationError(_("Missing company codes: %r") % list(missing_company_codes))

        values = []
        for record in self:
            value = {"Name": record.name}
            if not to_update:
                value.update({
                    "Code": record.category_code
                })

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

        if to_update:
            return values
        return bravo_column_names, values

    def bravo_get_update_value_for_existing_record(self):
        column_names, values = self.bravo_get_update_values(True)
        if values:
            return values[0]
        return {}

    def bravo_get_insert_values(self):
        return self.bravo_get_record_values()

    def bravo_get_update_values(self, values):
        res = self.bravo_get_record_values(to_update=True)
        if not res:
            return {}
        return res[0]

    def bravo_filter_record_by_level(self, level):
        return self.filtered(lambda rec: len(re.findall('/', rec.parent_path)) == level)

    def bravo_get_inset_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            insert_sql = records.with_context(**{CONTEXT_CATEGORY_KEY: level}).bravo_get_insert_sql()
            queries.extend(insert_sql)
        return queries

    def bravo_get_insert_sql(self):
        if self.env.context.get(CONTEXT_CATEGORY_KEY):
            return super().bravo_get_insert_sql()
        return self.bravo_get_inset_sql_all_level()

    def bravo_get_update_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            update_sql = records.with_context(**{CONTEXT_CATEGORY_KEY: level}).bravo_get_update_sql(None)
            queries.extend(update_sql)
        return queries

    def bravo_get_update_sql(self, values=None):
        if self.env.context.get(CONTEXT_CATEGORY_KEY):
            return super().bravo_get_update_sql(values)
        return self.bravo_get_update_sql_all_level()

    def bravo_get_insert_with_check_existing_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            update_sql = records.with_context(
                **{CONTEXT_CATEGORY_KEY: level}).bravo_get_insert_with_check_existing_sql()
            queries.extend(update_sql)
        return queries

    def bravo_get_insert_with_check_existing_sql(self):
        if self.env.context.get(CONTEXT_CATEGORY_KEY):
            return super().bravo_get_insert_with_check_existing_sql()
        return self.bravo_get_insert_with_check_existing_sql_all_level()

    def bravo_get_delete_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            delete_sql = records.with_context(**{CONTEXT_CATEGORY_KEY: level}).bravo_get_delete_sql()
            queries.extend(delete_sql)
        return queries

    def bravo_get_delete_sql(self):
        if self.env.context.get(CONTEXT_CATEGORY_KEY):
            return super().bravo_get_delete_sql()
        return self.bravo_get_delete_sql_all_level()
