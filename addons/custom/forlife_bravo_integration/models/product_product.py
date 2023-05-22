# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField

import re


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'bravo.model']
    _bravo_table = 'B20Item'

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

    def bravo_get_record_values(self, to_update=False, **kwargs):
        def check_account_is_155x(account_code):
            if not account_code:
                return False
            return re.match('^155.*', account_code)

        company_by_code = self.bravo_get_companies()
        values = []
        bravo_column_names = [
            "Code", "Name", "ParentCode", "UnitCode",
            "BrandCode", "ItemGroupCode", "ItemLineCode", "StructureCode", "CommodityGroup",
            "ItemType"
        ]
        attribute_column_names = [
            "Object", "BrandName", "MainFabric", "Subclass1", "Subclass2", "Subclass3", "Subclass4", "Subclass5",
            "Subclass6", "Subclass7", "Subclass8", "Subclass9", "Subclass10", "Attribute1", "Attribute2", "Designer",
            "Origin", "Source", "YearOfManu", "SeasonCode", "TypeOfGoods", "ColorDesc", "SizeRange", "Reproduce",
            "QualityCode", "Guide", "ColorLight",
        ]
        bravo_column_names.extend(attribute_column_names)
        attribute_column_name_code_mapping = {
            "Object": "001",
            "BrandName": "002",
            "MainFabric": "003",
            "Subclass1": "004",
            "Subclass2": "005",
            "Subclass3": "006",
            "Subclass4": "007",
            "Subclass5": "008",
            "Subclass6": "009",
            "Subclass7": "010",
            "Subclass8": "011",
            "Subclass9": "012",
            "Subclass10": "013",
            "Attribute1": "014",
            "Attribute2": "015",
            "Designer": "016",
            "Origin": "017",
            "Source": "018",
            "YearOfManu": "019",
            "SeasonCode": "020",
            "TypeOfGoods": "021",
            "ColorDesc": "022",
            "SizeRange": "023",
            "Reproduce": "024",
            "QualityCode": "025",
            "Guide": "026",
            "ColorLight": "027",
        }
        for record in self:
            category_level_5 = record.categ_id
            category_level_4 = category_level_5.parent_id
            category_level_3 = category_level_4.parent_id
            category_level_2 = category_level_3.parent_id
            category_level_1 = category_level_2.parent_id
            value = {
                bravo_column_names[0]: record.barcode,
                bravo_column_names[1]: record.name,
                bravo_column_names[2]: record.sku_code,
                bravo_column_names[3]: record.uom_id.code,
                bravo_column_names[4]: category_level_1.category_code,
                bravo_column_names[5]: category_level_2.category_code,
                bravo_column_names[6]: category_level_3.category_code,
                bravo_column_names[7]: category_level_4.category_code,
                bravo_column_names[8]: category_level_5.category_code,
            }
            if record.detailed_type != 'product':
                product_type = 0
            else:
                exist_155_accounts = any([
                    check_account_is_155x(
                        record.with_company(company_by_code['1300'].sudo()).property_stock_valuation_account_id.code),
                    check_account_is_155x(
                        record.with_company(company_by_code['1200'].sudo()).property_stock_valuation_account_id.code),
                    check_account_is_155x(
                        record.with_company(company_by_code['1400'].sudo()).property_stock_valuation_account_id.code),
                    check_account_is_155x(
                        record.with_company(company_by_code['1100'].sudo()).property_stock_valuation_account_id.code),
                ])
                product_type = 1 if exist_155_accounts else 2
            value.update({
                bravo_column_names[9]: product_type
            })

            attribute_values = record.product_template_variant_value_ids.mapped('product_attribute_value_id')
            product_attribute_code_value_mapping = {}
            for attr_value in attribute_values:
                attribute_code = attr_value.attribute_id.attrs_code
                product_attribute_code_value_mapping.update({
                    attribute_code: attr_value.name
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

        return bravo_column_names, values
