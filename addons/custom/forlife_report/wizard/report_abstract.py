# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ReportAbstract(models.TransientModel):
    _name = 'report.abstract'
    _description = 'Report Abstract'

    def _get_query_params(self):
        return []

    def _get_query(self):
        return """select count(*) from res_partner"""

    def get_report_data(self):
        query = self._get_query()
        query_params = self._get_query_params()
        data = self.env.cr.execute(query, query_params)
        return data

    def view_report(self):
        ...

    def print_xlsx(self):
        ...
