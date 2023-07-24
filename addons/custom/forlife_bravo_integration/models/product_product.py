# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField
from odoo.addons.forlife_bravo_integration.models.product_category import CONTEXT_CATEGORY_ACCOUNT_KEY

import re


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'bravo.model.update.action']
    _bravo_field_sync = ['name', 'sku_code', 'uom_id', 'categ_id', 'attribute_line_ids']

    def write(self, values):
        res = super().write(values)
        if self.bravo_check_need_sync(list(values.keys())):
            queries = self.product_variant_ids.bravo_get_update_sql(values)
            if queries:
                self.env['product.product'].sudo().with_delay(channel="root.Bravo").bravo_execute_query(queries)
        return res


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'bravo.model']
    _bravo_table = 'B20Item'
    _bravo_field_sync = ['barcode']

    def bravo_get_companies(self):
        company_codes = ['1100', '1200', '1300', '1400']
        companies = self.env['res.company'].sudo().search([('code', 'in', company_codes)])
        company_by_code = {c.code: c for c in companies}
        missing_company_codes = set(company_codes) - set(company_by_code.keys())
        if missing_company_codes:
            raise ValidationError(_("Missing company codes: %r") % list(missing_company_codes))
        return company_by_code

    def bravo_get_identity_key_values(self):
        records = self.bravo_filter_records()
        res = []
        for record in records:
            value = {'Code': record.barcode}
            res.append(value)
        return res

    def bravo_get_identity_key_names(self):
        return ['Code']

    def bravo_get_product_category_hierarchy(self, product):
        category_object = self.env['product.category']
        accounting_category = product.categ_id if product.categ_id.is_accounting_category else category_object
        category_ids = [x for x in product.categ_id.parent_path.split('/') if x]
        category_level = [int(x) for x in category_ids]
        len_category = len(category_level)
        category_level_1 = category_object.browse(category_level[0]) if len_category > 0 else category_object
        category_level_2 = category_object.browse(category_level[1]) if len_category > 1 else category_object
        category_level_3 = category_object.browse(category_level[2]) if len_category > 2 else category_object
        category_level_4 = category_object.browse(category_level[3]) if len_category > 3 else category_object
        return category_level_1, category_level_2, category_level_3, category_level_4, accounting_category

    def bravo_get_record_values(self, to_update=False, **kwargs):
        def check_account_is_155x(account_code):
            if not account_code:
                return False
            return re.match('^155.*', account_code)

        company_by_code = self.bravo_get_companies()
        values = []
        bravo_column_names = [
            "Code", "Name", "ParentCode", "UnitCode",
            "BrandCode", "CommodityGroup", "ItemLineCode", "StructureCode", "ItemGroupCode",
            "ItemType"
        ]
        attribute_column_names = [
            "SeasonCode"
        ]
        bravo_column_names.extend(attribute_column_names)
        attribute_column_name_code_mapping = {
            "SeasonCode": "AT027",
        }
        if not self:
            if to_update:
                return []
            return bravo_column_names, []
        for record in self:
            c1, c2, c3, c4, accounting_c = self.bravo_get_product_category_hierarchy(record)
            value = {
                bravo_column_names[0]: record.barcode or None,
                bravo_column_names[1]: record.name,
                bravo_column_names[2]: record.sku_code or record.product_tmpl_id.sku_code or None,
                bravo_column_names[3]: record.uom_id.code or None,
                bravo_column_names[4]: c1.bravo_get_category_code() or None,
                bravo_column_names[5]: c2.bravo_get_category_code() or None,
                bravo_column_names[6]: c3.bravo_get_category_code() or None,
                bravo_column_names[7]: c4.bravo_get_category_code() or None,
                bravo_column_names[8]: accounting_c.bravo_get_category_code(**{CONTEXT_CATEGORY_ACCOUNT_KEY: True}) or None,
            }
            if record.detailed_type != 'product':
                product_type = 0
            else:
                exist_155_accounts = any([
                    check_account_is_155x(
                        record.with_company(
                            company_by_code['1300'].sudo()).categ_id.property_stock_valuation_account_id.code),
                    check_account_is_155x(
                        record.with_company(
                            company_by_code['1200'].sudo()).categ_id.property_stock_valuation_account_id.code),
                    check_account_is_155x(
                        record.with_company(
                            company_by_code['1400'].sudo()).categ_id.property_stock_valuation_account_id.code),
                    check_account_is_155x(
                        record.with_company(
                            company_by_code['1100'].sudo()).categ_id.property_stock_valuation_account_id.code),
                ])
                product_type = 1 if exist_155_accounts else 2
            value.update({
                bravo_column_names[9]: product_type
            })

            attribute_values = record.product_tmpl_id.valid_product_template_attribute_line_ids
            product_attribute_code_value_mapping = {}
            for attr_value in attribute_values:
                if attr_value.value_count < 1:
                    continue
                # get only one value from attribute values
                attribute_code = attr_value.attribute_id.attrs_code
                product_attribute_code_value_mapping.update({
                    attribute_code: attr_value.value_ids[0].code
                })

            for attribute_name_column in attribute_column_names:
                attribute_code = attribute_column_name_code_mapping.get(attribute_name_column)
                if attribute_code in product_attribute_code_value_mapping:
                    value.update({
                        attribute_name_column: product_attribute_code_value_mapping[attribute_code]
                    })
                else:
                    value.update({
                        attribute_name_column: None
                    })

            values.append(value)

        if to_update:
            return values

        return bravo_column_names, values

    def bravo_get_insert_values(self, **kwargs):
        return self.bravo_get_record_values(**kwargs)

    def bravo_get_update_values(self, values, **kwargs):
        res = self.bravo_get_record_values(to_update=True, **kwargs)
        if not res:
            return {}
        return res[0]

    def bravo_get_update_value_for_existing_record(self, **kwargs):
        values = self.bravo_get_update_values(True, **kwargs)
        if values:
            return values[0] if type(values) is list else values
        return {}
