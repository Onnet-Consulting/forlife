# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re

CONTEXT_CATEGORY_KEY = 'bravo_product_category_level'
CONTEXT_CATEGORY_ACCOUNT_KEY = 'bravo_product_category_need_accounts'


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'bravo.model']
    _bravo_field_sync = [
        'is_accounting_category', 'code', 'name', 'property_stock_valuation_account_id',
        'property_account_expense_categ_id', 'property_account_income_categ_id'
    ]

    is_accounting_category = fields.Boolean(string='Là nhóm hạch toán', default=False)

    def bravo_get_category_code(self, **kwargs):
        if not self:
            return None
        self.ensure_one()
        category_code = self.category_code or ''
        if self.is_accounting_category and kwargs.get(CONTEXT_CATEGORY_ACCOUNT_KEY):
            return category_code[-4:]
        return category_code

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

    def bravo_get_identity_key_values(self, **kwargs):
        records = self.bravo_filter_records()
        res = []
        for record in records:
            value = {'Code': record.bravo_get_category_code(**kwargs)}
            res.append(value)
        return res

    def bravo_get_identity_key_names(self):
        return ['Code']

    def bravo_get_record_values(self, to_update=False, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_ACCOUNT_KEY):
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
                        "Code": record.bravo_get_category_code(**kwargs)
                    })

                record_1300 = record.with_company(company_by_code['1300']).sudo()
                value.update({
                    "ItemAccount": record_1300.property_stock_valuation_account_id.code,
                    "COGSAccount": record_1300.property_account_expense_categ_id.code,
                    "SalesAccount": record_1300.property_account_income_categ_id.code,
                })
                record_1200 = record.with_company(company_by_code['1200']).sudo()
                value.update({
                    "ItemAccount1": record_1200.property_stock_valuation_account_id.code,
                    "COGSAccount1": record_1200.property_account_expense_categ_id.code,
                    "SalesAccount1": record_1200.property_account_income_categ_id.code,
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
        else:
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
                        "Code": record.bravo_get_category_code(**kwargs)
                    })
                values.append(value)

            if to_update:
                return values
            return bravo_column_names, values

    def bravo_get_update_value_for_existing_record(self, **kwargs):
        values = self.bravo_get_update_values(True, **kwargs)
        if values:
            return values[0] if type(values) is list else values
        return {}

    def bravo_get_insert_values(self, **kwargs):
        return self.bravo_get_record_values(**kwargs)

    def bravo_get_update_values(self, values, **kwargs):
        res = self.bravo_get_record_values(to_update=True, **kwargs)
        if not res:
            return {}
        return res[0]

    def bravo_filter_record_by_level(self, level):
        return self.filtered(lambda rec: len(re.findall('/', rec.parent_path)) == level)

    def bravo_filter_record_need_send_account(self):
        return self.filtered(lambda rec: rec.is_accounting_category)

    def bravo_get_inset_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            insert_sql = records.bravo_get_insert_sql(**{CONTEXT_CATEGORY_KEY: level})
            queries.extend(insert_sql)

        records = self.bravo_filter_record_need_send_account()
        insert_sql = records.bravo_get_insert_sql(**{CONTEXT_CATEGORY_ACCOUNT_KEY: True})
        queries.extend(insert_sql)

        exist_queries = []
        exist_params = []
        res = []
        for que, par in queries:
            if que in exist_queries and par in exist_params:
                continue
            exist_queries.append(que)
            exist_params.append(par)
            res.append((que, par))
        return res

    def bravo_get_insert_sql(self, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_KEY) or kwargs.get(CONTEXT_CATEGORY_ACCOUNT_KEY):
            return super().bravo_get_insert_sql(**kwargs)
        return self.bravo_get_inset_sql_all_level()

    def bravo_get_update_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            update_sql = records.bravo_get_update_sql(None, **{CONTEXT_CATEGORY_KEY: level})
            queries.extend(update_sql)

        records = self.bravo_filter_record_need_send_account()
        update_sql = records.bravo_get_update_sql(None, **{CONTEXT_CATEGORY_ACCOUNT_KEY: True})
        queries.extend(update_sql)
        return queries

    def bravo_get_update_sql(self, values=None, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_KEY) or kwargs.get(CONTEXT_CATEGORY_ACCOUNT_KEY):
            return super().bravo_get_update_sql(values, **kwargs)
        return self.bravo_get_update_sql_all_level()

    def bravo_get_insert_with_check_existing_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            update_sql = records.bravo_get_insert_with_check_existing_sql(**{CONTEXT_CATEGORY_KEY: level})
            queries.extend(update_sql)

        records = self.bravo_filter_record_need_send_account()
        category_accounts_update_sql = records.bravo_get_insert_with_check_existing_sql(
            **{CONTEXT_CATEGORY_ACCOUNT_KEY: True})
        queries.extend(category_accounts_update_sql)
        exist_queries = []
        exist_params = []
        res = []
        for que, par in queries:
            if que in exist_queries and par in exist_params:
                continue
            exist_queries.append(que)
            exist_params.append(par)
            res.append((que, par))
        return res

    def bravo_get_insert_with_check_existing_sql(self, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_KEY) or kwargs.get(CONTEXT_CATEGORY_ACCOUNT_KEY):
            return super().bravo_get_insert_with_check_existing_sql(**kwargs)

        return self.bravo_get_insert_with_check_existing_sql_all_level()

    def bravo_get_delete_sql_all_level(self):
        queries = []
        for level in [1, 2, 3, 4]:
            records = self.bravo_filter_record_by_level(level)
            delete_sql = records.bravo_get_delete_sql(**{CONTEXT_CATEGORY_KEY: level})
            queries.extend(delete_sql)

        records = self.bravo_filter_record_need_send_account()
        delete_sql = records.bravo_get_delete_sql(**{CONTEXT_CATEGORY_ACCOUNT_KEY: True})
        queries.extend(delete_sql)

        return queries

    def bravo_get_delete_sql(self, **kwargs):
        if kwargs.get(CONTEXT_CATEGORY_KEY) or kwargs.get(CONTEXT_CATEGORY_ACCOUNT_KEY):
            return super().bravo_get_delete_sql(**kwargs)
        return self.bravo_get_delete_sql_all_level()
