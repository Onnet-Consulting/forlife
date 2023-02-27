# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import pyodbc


class MssqlServer(models.TransientModel):
    _name = "mssql.server"
    _description = 'MSSQL Server'

    def _conn(self, autocommit=True, encrypt="no"):
        """
        @param autocommit: https://github.com/mkleehammer/pyodbc/wiki/Database-Transaction-Management
        """
        ir_config = self.env['ir.config.parameter'].sudo()
        driver = ir_config.get("mssql.driver")
        host = ir_config.get("mssql.host")
        database = ir_config.get("mssql.database")
        username = ir_config.get("mssql.username")
        password = ir_config.get("mssql.password")
        return pyodbc.connect(
            f'DRIVER={driver};SERVER={host};DATABASE={database};UID={username};PWD={password};ENCRYPT={encrypt}',
            autocommit=autocommit)

    def execute(self, query, autocommit=True):
        with self._conn(autocommit=autocommit) as conn:
            cursor = conn.cursor()
            if type(query) in [list, tuple]:
                for q in query:
                    cursor.execute(q)
            else:
                cursor.execute(query)
            if not autocommit:
                conn.commit()
            return True

    def execute_read(self, query, size=1000):
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            while True:
                data = cursor.fetchmany(size)
                yield data
                if not data:
                    break

