# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ..fields import BravoCharField, BravoDatetimeField, BravoMany2oneField

import re


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'bravo.model']
    _bravo_table = 'B20Item'

    def bravo_get_identity_key_values(self):
        records = self.bravo_filter_records()
        res = []
        for record in records:
            value = {'Code': record.barcode}
            res.append(value)
        return res

    def bravo_get_identity_key_names(self):
        return ['Code']

    def bravo_get_record_values(self, to_update=False):
        bravo_column_names = [
            'Code', 'Name',
            'UnitCode', 'ItemType',
            'BrandCode', 'ItemGroupCode', 'ItemLineCode', 'StructureCode',
            'Object', 'BrandName', 'SizeRange', 'ColorDesc', 'MainFabric', 'QualityCode', 'ColorLight', 'Subclass1',
            'Subclass2', 'Subclass3', 'Subclass4', 'Subclass5', 'Subclass6', 'Subclass7', 'Subclass8', 'Subclass9',
            'Subclass10', 'Attribute1', 'Attribute2', 'Designer', 'Origin', 'Source', 'YearOfManu', 'SeasonCode',
            'TypeOfGoods', 'Guide', 'Reproduce',
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
            value = {
                "Name": record.Name,
                "UnitCode": record.uom_id.code
            }
            if not to_update:
                value.update({
                    "Code": record.barcode
                })

            category = record.categ_id
            value.update({
                'BrandCode': category.parent_id.parent_id.parent_id.code,
                'ItemGroupCode': category.parent_id.parent_id.code,
                'ItemLineCode': category.parent_id.code,
                'StructureCode': category.code,
            })

            if record.detailed_type in ['consu', 'service', 'asset']:
                detailed_type = 0
            else:
                pass

