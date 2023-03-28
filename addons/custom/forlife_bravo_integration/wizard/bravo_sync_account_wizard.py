# -*- coding:utf-8 -*-

from odoo import api, fields, models

BRAVO_ACCOUNT_TABLE = 'B20ChartOfAccount'

class BravoSyncAccountWizard(models.TransientModel):
    """
    Synchronize accounts from Bravo to all Company
    """
    _name = 'bravo.sync.account.wizard'
    _inherit = ['mssql.server']
    _description = 'Bravo Synchronize account wizard'

    company_ids = fields.Many2many('res.company', 'bravo_sync_account_compan_rel', 'sync_id', 'cid',
                                   string='Companies', default=lambda self: self.env.companies.ids)

    # TODO: reload form after click this button
    def sync(self):
        self.ensure_one()
        self.install_coa()
        self.insert_accounts()
        self.archive_vn_template_accounts()

    # TODO: reload form after click this button
    def sync_updated(self):
        self.ensure_one()
        self.insert_missing_accounts()

    def install_coa(self):
        companies = self.company_ids
        vn_account_chart_template = self.env.ref('l10n_vn.vn_template')
        for company in companies:
            vn_account_chart_template.try_loading(company, install_demo=False)

    def insert_accounts(self):
        accounts = self.get_bravo_accounts()
        companies = self.company_ids
        for company in companies:
            self.env['account.account'].with_company(company).sudo().create(accounts)
        return True

    def insert_missing_accounts(self):
        companies = self.company_ids
        for company in companies:
            self.insert_odoo_missing_accounts(company)
        return True

    def archive_vn_template_accounts(self):
        """Set all accounts in l10n_vn module to deprecated"""
        res_ids = self.env['ir.model.data'].sudo().search([
            ('model', '=', 'account.account'), ('module', '=', 'l10n_vn')
        ]).mapped('res_id')
        companies = self.company_ids
        for company in companies:
            self.env['account.account'].with_company(company).sudo(). \
                search([('company_id', '=', company.id), ('id', 'in', res_ids)]).write({'deprecated': True})
        return True

    def get_bravo_accounts(self):
        accounts = []
        query = """
            SELECT Code, Name
            FROM %s
        """ % BRAVO_ACCOUNT_TABLE
        data = self._execute_read(query)
        field_names = ['code', 'name']
        for chunk_data in data:
            accounts.extend([dict(zip(field_names, cdata)) for cdata in chunk_data])
        return accounts

    def get_odoo_missing_accounts(self, company):
        odoo_account_codes = self.env['account.account'].sudo().search([('company_id', '=', company.id)]).mapped('code')
        accounts = []
        if not odoo_account_codes:
            query = """
                SELECT Code, Name
                FROM %s
            """ % BRAVO_ACCOUNT_TABLE
        else:
            query = """
                SELECT Code, Name
                FROM %s
                Where Code not in (%s)
            """ % (BRAVO_ACCOUNT_TABLE, ','.join(['?'] * len(odoo_account_codes)))
        data = self._execute_read(query, params=odoo_account_codes)
        field_names = ['code', 'name']
        for chunk_data in data:
            accounts.extend([dict(zip(field_names, cdata)) for cdata in chunk_data])
        return accounts

    def insert_odoo_missing_accounts(self, company):
        odoo_missing_accounts = self.get_odoo_missing_accounts(company)
        self.env['account.account'].with_company(company).sudo().create(odoo_missing_accounts)
        return True
