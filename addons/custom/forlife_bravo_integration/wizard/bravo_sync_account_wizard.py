# -*- coding:utf-8 -*-

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)

BRAVO_ACCOUNT_TABLE = 'B20ChartOfAccount'


class BravoSyncAccountWizard(models.TransientModel):
    """
    Synchronize accounts from Bravo to all Company
    """
    _name = 'bravo.sync.account.wizard'
    _inherit = ['mssql.server']
    _description = 'Bravo Synchronize account wizard'

    def sync(self):
        self.ensure_one()
        companies = self.env['res.company'].search([])
        bravo_accounts = self.get_bravo_accounts()
        for company in companies:
            self = self.with_company(company).sudo()
            self.install_coa()
            self.insert_accounts(bravo_accounts)
            # self.archive_vn_template_accounts()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def install_coa(self):
        vn_account_chart_template = self.env.ref('l10n_vn.vn_template')
        vn_account_chart_template.try_loading(self.env.company, install_demo=False)

    def insert_accounts(self, bravo_accounts):
        account_account = self.env['account.account']
        bravo_account_codes = [ba['code'] for ba in bravo_accounts]
        exist_odoo_account_codes = account_account.search(
            [('code', 'in', bravo_account_codes), ('company_id', '=', self.env.company.id)]).mapped('code')
        newly_bravo_accounts = [ba for ba in bravo_accounts if ba['code'] not in exist_odoo_account_codes]
        self.env['account.account'].create(newly_bravo_accounts)
        return True

    def archive_vn_template_accounts(self):
        """Set all accounts in l10n_vn module to deprecated"""
        res_ids = self.env['ir.model.data'].sudo().search([
            ('model', '=', 'account.account'), ('module', '=', 'l10n_vn')
        ]).mapped('res_id')
        company = self.env.company
        self.env['account.account'].sudo(). \
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
