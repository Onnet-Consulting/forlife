# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class ProductCategory(models.Model):
    _inherit = 'product.category'

    # _name = 'product.category'
    # _inherit = ['product.category', 'bravo.model']

    @api.model
    def get_bravo_table_by_level(self, level):
        if level == 4:
            bravo_table = 'B20Structure'
        elif level == 3:
            bravo_table = 'B20ItemLine'
        elif level == 2:
            bravo_table = 'B20ItemGroup'
        else:
            bravo_table = 'B20Brand'
        return bravo_table

    def get_bravo_values_by_level(self, level):
        records = self.filter_bravo_records()
        bravo_table = self.get_bravo_table_by_level(level)
        records = records.filtered(lambda rec: len(re.findall('/', rec.parent_path)) == level)
        company_codes = ['1100', '1200', '1400', '1500']
        companies = self.env['res.company'].sudo().search([('code', 'in', company_codes)])
        company_by_code = {c.code: c for c in companies}
        missing_company_codes = set(company_codes) - set(company_by_code.keys())
        if missing_company_codes:
            raise ValidationError(_("Missing company codes: %r") % list(missing_company_codes))
        bravo_column_names = [
            "Code", "Name",
            "ItemAccount", "COGSAccount", "SalesAccount",
            "ItemAccount1", "COGSAccount1", "SalesAccount1",
            "ItemAccount2", "COGSAccount2", "SalesAccount2",
            "ItemAccount3", "COGSAccount3", "SalesAccount3",
        ]
        values = []
        for record in records:
            value = {"Code": record.category_code, "Name": record.name}
            record_1200 = record.with_company(company_by_code['1200'])
            value.update({
                "ItemAccount": record_1200.property_stock_valuation_account_id.code,
                "COGSAccount": record_1200.property_account_expense_categ_id.code,
                "SalesAccount": record_1200.property_account_income_categ_id.code,
            })
            record_1400 = record.with_company(company_by_code['1400'])
            value.update({
                "ItemAccount1": record_1400.property_stock_valuation_account_id.code,
                "COGSAccount1": record_1400.property_account_expense_categ_id.code,
                "SalesAccount1": record_1400.property_account_income_categ_id.code,
            })
            record_1500 = record.with_company(company_by_code['1500'])
            value.update({
                "ItemAccount2": record_1500.property_stock_valuation_account_id.code,
                "COGSAccount2": record_1500.property_account_expense_categ_id.code,
                "SalesAccount2": record_1500.property_account_income_categ_id.code,
            })
            record_1100 = record.with_company(company_by_code['1100'])
            value.update({
                "ItemAccount3": record_1100.property_stock_valuation_account_id.code,
                "COGSAccount3": record_1100.property_account_expense_categ_id.code,
                "SalesAccount3": record_1100.property_account_income_categ_id.code,
            })
            values.append(value)
        return bravo_table, bravo_column_names, values


    def write(self, vals):
        return super().write(vals)
