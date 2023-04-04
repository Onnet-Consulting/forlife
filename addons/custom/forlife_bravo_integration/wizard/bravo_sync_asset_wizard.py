# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BravoSyncAssetWizard(models.TransientModel):
    _name = 'bravo.sync.asset.wizard'
    _inherit = 'mssql.server'
    _description = 'Bravo synchronize Assets wizard'

    def sync(self):
        # FIXME: push this function to queue job cron
        companies = self.env['res.company'].search_read([('code', '!=', False)], ['code'])
        for company_data in companies:
            self.create_odoo_data(company_data)
        return True

    @api.model
    def mapping_bravo_with_odoo_fields(self):
        return {
            'Type': 'type',
            'Code': 'code',
            'CardNo': 'card_no',
            'ItemCode': 'item_code',
            'Name': 'name',
            'Unit': 'unit',
            'Capacity': 'capacity',
            'MadeYear': 'made_year',
            'MadeIn': 'made_in',
            'AssetAccount': 'asset_account',
            'UsefulMonth': 'use_ful_month',
            'DocDate': 'doc_date',
            'OriginalCost': 'original_cost',
            'DeprDebitAccount': 'depr_debit_account',
            'DeprCreditAccount': 'depr_credit_account',
            'DeptCode': 'dept_code',
            'Comment': 'comment',
            'LocationCode': 'location',
            'Quantity': 'quantity',
            'EmployeeCode': 'employee',
            'ElavationGroup1': 'elavation_group_1',
            'ElavationGroup2': 'elavation_group_2',
            'ElavationGroup3': 'elavation_group_3',
            'CompanyCode': 'company_id',
            'PushDate': 'bravo_create_date',
        }

    @api.model
    def get_asset_last_create_date_by_company(self, company_data):
        cr = self.env.cr
        query = """
            SELECT max(bravo_create_date)
            FROM assets_assets
            WHERE company_id = %s
        """
        cr.execute(query, [company_data['id']])
        return cr.fetchone()[0]

    @api.model
    def get_new_bravo_data_by_company(self, company_data):
        bravo_table = 'B20Asset'
        mapping_bravo_odoo_fields = self.mapping_bravo_with_odoo_fields()
        bravo_assets_columns = list(mapping_bravo_odoo_fields.keys())
        bravo_assets_columns_str = ','.join(bravo_assets_columns)
        odoo_last_create_data = self.get_asset_last_create_date_by_company(company_data)
        company_code = company_data.get('code')
        company_id = company_data.get('id')
        if not odoo_last_create_data:
            select_query = """
                SELECT %s
                FROM %s
                WHERE CompanyCode = ?
            """ % (bravo_assets_columns_str, bravo_table)
            data = self._execute_many_read([(select_query, [company_code])])
        else:
            select_query = """
                SELECT %s
                FROM %s
                WHERE PushDate > ? AND CompanyCode = ?
            """ % (bravo_assets_columns_str, bravo_table)
            data = self._execute_many_read([(select_query, [odoo_last_create_data, company_code])])
        res = []
        analytic_account_codes = []
        asset_location_codes = []
        employee_codes = []
        for records in data:
            for rec in records:
                rec_value = dict(zip(bravo_assets_columns, rec))
                analytic_account_codes.append(rec_value.get('DeptCode'))
                asset_location_codes.append(rec_value.get('LocationCode'))
                employee_codes.append(rec_value.get('EmployeeCode'))
                res.append(rec_value)
        if not res:
            return False

        analytic_account_id_by_code = self.generate_analytic_account_id_by_code(company_data, analytic_account_codes)
        asset_location_id_by_code = self.generate_asset_location_id_by_code(asset_location_codes)
        employee_id_by_code = self.generate_hr_employee_id_by_code(company_data, employee_codes)

        for record_value in res:
            record_value['DeptCode'] = analytic_account_id_by_code[record_value['DeptCode']]
            record_value['LocationCode'] = asset_location_id_by_code[record_value['LocationCode']]
            record_value['EmployeeCode'] = employee_id_by_code[record_value['EmployeeCode']]
            record_value['CompanyCode'] = company_id

        return res

    def generate_company_id_by_code(self):
        companies = self.env['res.company'].search([('code', '!=', False)])
        return {comp.code: comp.id for comp in companies}

    def generate_analytic_account_id_by_code(self, company_data, codes):
        analytic_accounts = self.env['account.analytic.account'].search([
            ('code', 'in', codes),
            ('company_id', '=', company_data['id'])
        ])
        res = {}
        for aa in analytic_accounts:
            res[aa.code] = aa.id
        missing_codes = list(set(codes) - set(res.keys()))
        if missing_codes:
            raise ValidationError(_("Missing analytic codes: %r") % missing_codes)
        return res

    def generate_asset_location_id_by_code(self, codes):
        asset_locations = self.env['asset.location'].search([('code', 'in', codes)])
        res = {}
        for asl in asset_locations:
            res[asl.code] = asl.id
        missing_codes = list(set(codes) - set(res.keys()))
        if missing_codes:
            raise ValidationError(_("Missing asset location codes: %r") % missing_codes)
        return res

    def generate_hr_employee_id_by_code(self, company_data, codes):
        employees = self.env['hr.employee'].search([
            ('code', 'in', codes),
            ('company_id', '=', company_data['id'])
        ])
        res = {}
        for emp in employees:
            res[emp.code] = emp.id
        missing_codes = list(set(codes) - set(res.keys()))
        if missing_codes:
            raise ValidationError(_("Missing employee codes: %r") % missing_codes)
        return res

    @api.model
    def generate_odoo_data(self, company_data):
        bravo_data = self.get_new_bravo_data_by_company(company_data)
        if not bravo_data:
            return False
        mapping_bravo_odoo_fields = self.mapping_bravo_with_odoo_fields()
        odoo_values = []
        for rec in bravo_data:
            value = {}
            for bravo_column, odoo_column in mapping_bravo_odoo_fields.items():
                value.update({odoo_column: rec.get(bravo_column)})
            odoo_values.append(value)
        return odoo_values

    def create_odoo_data(self, company_data):
        company = self.env['res.company'].browse(company_data.get('id'))
        self = self.sudo().with_company(company)
        odoo_data = self.generate_odoo_data(company_data)
        if not odoo_data:
            return False
        self.env['assets.assets'].create(odoo_data)
        return True
