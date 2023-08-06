# -*- coding:utf-8 -*-

from odoo import api, fields, models
import json
import ast


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def bravo_get_default_list_model(self):
        model = [
            'res.brand', 'uom.uom', 'account.analytic.account', 'product.attribute.value', 'product.category',
            'res.currency.rate', 'warehouse.group', 'stock.warehouse', 'stock.location', 'product.product',
            'asset.location', 'assets.assets', 'expense.category', 'expense.item', 'forlife.production',
            'hr.employee', 'occasion.group', 'occasion.code', 'res.partner.group', 'res.partner',
        ]
        if self._context.get('list_model'):
            return model
        return json.dumps(model)

    mssql_driver = fields.Char(string='Driver Name', config_parameter="mssql.driver",
                               default='ODBC Driver 18 for SQL Server', required=True)
    mssql_host = fields.Char(string='Server', config_parameter="mssql.host", default='localhost', required=True)
    mssql_database = fields.Char(string='Database', config_parameter="mssql.database", required=True, default="master")
    mssql_username = fields.Char(string='Username', config_parameter="mssql.username", default='sa', required=True)
    mssql_password = fields.Char(string='Password', config_parameter="mssql.password", required=True, default="admin")
    integration_bravo_up = fields.Boolean(string='Hoạt động', config_parameter="integration.bravo.up", default=False)
    list_model_sync_bravo = fields.Char("Danh sách đối tượng", config_parameter="list.model.sync.bravo", default=bravo_get_default_list_model)

    @api.model
    def sync_all_master_data_for_bravo(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        models = ast.literal_eval(ir_config.get_param("list.model.sync.bravo")) or []
        if not models:
            models = self.with_context(list_model=True).bravo_get_default_list_model()
        for model in models:
            domain = self.env[model].bravo_get_filter_domain()
            records = self.env[model].search(domain)
            while records:
                record = records[:min(500, len(records))]
                record.sudo().with_delay(channel="root.Bravo").bravo_insert_with_check_existing()
                records = records - record
