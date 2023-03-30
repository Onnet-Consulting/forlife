# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class BravoSyncAssetWizard(models.Model):
    _name = 'bravo.sync.asset.wizard'
    _inherit = 'mssql.server'
    _description = 'Bravo synchronize Assets wizard'

    def sync(self):
        pass

    def get_odoo_last_push_date(self):
        cr = self.env.cr
        query = """
            SELECT max(push_date)
            FROM assets_assets
        """
        cr.execute(query)
        return cr.fetchone()


    def scan_bravo_data(self):
        select_query = """
            SELECT *
            FROM B20Asset
            WHERE PushDate >= %s
        """