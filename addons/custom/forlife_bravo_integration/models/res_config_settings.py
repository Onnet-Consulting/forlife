# -*- coding:utf-8 -*-

from odoo import api, fields, models
import json
import ast


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def bravo_get_domain_model(self):
        return [('model', 'in', ('res.brand', 'uom.uom', 'account.analytic.account', 'product.attribute.value', 'product.category',
                                 'res.currency.rate', 'warehouse.group', 'stock.warehouse', 'stock.location', 'product.product',
                                 'asset.location', 'assets.assets', 'expense.category', 'expense.item', 'forlife.production',
                                 'hr.employee', 'occasion.group', 'occasion.code', 'res.partner.group', 'res.partner'))]

    mssql_driver = fields.Char(string='Driver Name', config_parameter="mssql.driver",
                               default='ODBC Driver 18 for SQL Server', required=True)
    mssql_host = fields.Char(string='Server', config_parameter="mssql.host", default='localhost', required=True)
    mssql_database = fields.Char(string='Database', config_parameter="mssql.database", required=True, default="master")
    mssql_username = fields.Char(string='Username', config_parameter="mssql.username", default='sa', required=True)
    mssql_password = fields.Char(string='Password', config_parameter="mssql.password", required=True, default="admin")
    integration_bravo_up = fields.Boolean(string='Hoạt động', config_parameter="integration.bravo.up", default=False)
    model_ids = fields.Many2many('ir.model', string='Đối tượng đồng bộ', domain=bravo_get_domain_model)
    record_per_job = fields.Integer('Số bản ghi trên 1 queue job', default=500, help='Max: 500, Min: 1')
    with_multi_company = fields.Boolean('Trên nhiều công ty', default=False, help='Nếu tích chọn hệ thống tự động chạy tất cả dữ liệu của tất cả công ty')

    def sync_master_data_for_bravo(self):
        record_per_job = max(1, min(500, self.record_per_job))
        companies = self.env['res.company'].search([('code', '!=', False)])
        for model in self.model_ids:
            domain = self.env[model.model].bravo_get_filter_domain()
            if self.with_multi_company:
                for company in companies:
                    records = self.env[model.model].sudo().with_company(company).search(domain + [('company_id', '=', company.id)])
                    while records:
                        record = records[:min(record_per_job, len(records))]
                        record.sudo().with_company(company).with_delay(channel="root.Bravo").bravo_insert_with_check_existing()
                        records = records - record
            else:
                records = self.env[model.model].search(domain)
                while records:
                    record = records[:min(record_per_job, len(records))]
                    record.sudo().with_delay(channel="root.Bravo").bravo_insert_with_check_existing()
                    records = records - record
        self.model_ids = [(5, 0, 0)]
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_bravo_integration.sync_master_data_for_bravo_action')
        action['res_id'] = self.id
        return action
