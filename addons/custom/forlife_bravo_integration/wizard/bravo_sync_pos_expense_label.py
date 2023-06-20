# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BravoSyncLiquidationAssetWizard(models.TransientModel):
    _name = 'bravo.sync.liquidation.asset.wizard'
    _inherit = 'mssql.server'
    _description = 'Bravo synchronize Liquidation Assets wizard'

    def sync(self):
        companies = self.env['res.company'].search_read([('code', '!=', False)], ['code'])
        for company_data in companies:
            self.update_odoo_data(company_data)
        return True

    @api.model
    def update_odoo_data(self, company_data):
        bravo_data = self.get_update_asset_value_by_company(company_data)
        if not bravo_data:
            return False
        asset_asset = self.env['assets.assets'].sudo()
        for asset_id, data in bravo_data.items():
            asset_asset.browse(asset_id).write({
                'state': 'paid' if data[0] == 1 else 'using',
                'bravo_write_date': data[1]
            })
        return True

    @api.model
    def get_asset_last_write_date_by_company(self, company_data):
        """return latest updated asset"""
        cr = self.env.cr
        query = """
            SELECT max(bravo_write_date)
            FROM assets_assets
            WHERE company_id = %s
        """
        cr.execute(query, [company_data['id']])
        return cr.fetchone()[0]

    @api.model
    def get_update_asset_value_by_company(self, company_data):
        bravo_table = 'B30AssetLiquidation'
        update_asset_value_by_id = {}

        odoo_last_write_date = self.get_asset_last_write_date_by_company(company_data)
        company_code = company_data.get('code')
        bravo_assets_liquidation_columns = ["PushDate", "Active", "AssetCode"]
        bravo_assets_liquidation_columns_str = ','.join(bravo_assets_liquidation_columns)
        if not odoo_last_write_date:
            select_query = """
                SELECT %s
                FROM %s
                WHERE CompanyCode = ?
            """ % (bravo_assets_liquidation_columns_str, bravo_table)
            data = self._execute_many_read([(select_query, [company_code])])
        else:
            select_query = """
                SELECT %s
                FROM %s
                WHERE PushDate > ? AND CompanyCode = ?
            """ % (bravo_assets_liquidation_columns_str, bravo_table)
            data = self._execute_many_read([(select_query, [odoo_last_write_date, company_code])])
        bravo_values = []
        asset_codes = []
        for records in data:
            for rec in records:
                rec_value = dict(zip(bravo_assets_liquidation_columns, rec))
                bravo_asset_code = rec_value.get('AssetCode')
                if bravo_asset_code:
                    asset_codes.append(bravo_asset_code)
                bravo_values.append(rec_value)
        if not bravo_values:
            return False

        asset_id_by_code = self.generate_asset_id_by_code(company_data, asset_codes)
        for rec in bravo_values:
            update_asset_value_by_id.update({
                asset_id_by_code[rec['AssetCode']]: [rec['Active'], rec['PushDate']]
            })

        return update_asset_value_by_id

    def generate_asset_id_by_code(self, company_data, codes):
        assets = self.env['assets.assets'].search([
            ('code', 'in', codes),
            ('company_id', '=', company_data['id'])
        ])
        res = {}
        for acc in assets:
            res[acc.code] = acc.id
        missing_codes = list(set(codes) - set(res.keys()))
        if missing_codes:
            raise ValidationError(
                _("Missing Assets codes in company %s: %r") % (company_data.get('code'), missing_codes))
        return res
