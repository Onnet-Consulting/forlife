# -*- coding:utf-8 -*-

from odoo import api, fields, models


class BravoSyncAccountWizard(models.TransientModel):
    """
    Synchronize accounts from Bravo to all Company
    """
    _name = 'bravo.sync.account.wizard'
    _description = 'Bravo Synchronize account wizard'

    company_ids = fields.Many2many('res.company', 'bravo_sync_account_compan_rel', 'sync_id', 'cid',
                                   string='Companies', default=lambda self: self.env.companies.ids)

    def sync(self):
        self.ensure_one()
        self.install_coa()
        # install COA of vn for all company
        # create account for all company
        pass

    def install_coa(self):
        companies = self.company_ids
        vn_account_chart_template = self.env.ref('l10n_vn.vn_template')
        for company in companies:
            vn_account_chart_template.try_loading(company, install_demo=False)
