# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mssql_driver = fields.Char(string='Driver Name', config_parameter="mssql.driver",
                               default='ODBC Driver 18 for SQL Server', required=True)
    mssql_host = fields.Char(string='Server', config_parameter="mssql.host", default='localhost', required=True)
    mssql_database = fields.Char(string='Database', config_parameter="mssql.database", required=True, default="master")
    mssql_username = fields.Char(string='Username', config_parameter="mssql.username", default='sa', required=True)
    mssql_password = fields.Char(string='Password', config_parameter="mssql.password", required=True, default="admin")
