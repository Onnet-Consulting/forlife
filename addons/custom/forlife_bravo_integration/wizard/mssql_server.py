# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import pyodbc
from typing import Dict, List, Optional, Tuple, Union


class MssqlServer(models.AbstractModel):
    _name = "mssql.server"
    _description = 'MSSQL Server'

    @api.model
    def _conn(self, autocommit=True, encrypt="no"):
        """
        @param autocommit: https://github.com/mkleehammer/pyodbc/wiki/Database-Transaction-Management
        """
        ir_config = self.env['ir.config_parameter'].sudo()
        driver = ir_config.get_param("mssql.driver")
        host = ir_config.get_param("mssql.host")
        database = ir_config.get_param("mssql.database")
        username = ir_config.get_param("mssql.username")
        password = ir_config.get_param("mssql.password")
        return pyodbc.connect(
            f'DRIVER={driver};SERVER={host};DATABASE={database};UID={username};PWD={password};'
            f'ENCRYPT={encrypt};CHARSET=UTF8;', autocommit=autocommit)

    @api.model
    def _execute(self, query, params, autocommit=True):
        with self._conn(autocommit=autocommit) as conn:
            cursor = conn.cursor()
            if type(query) in [list, tuple]:
                for q in query:
                    cursor.execute(q)
            else:
                cursor.execute(query, params)
            if not autocommit:
                conn.commit()
            return True

    @api.model
    def _execute_many(self, queries):
        with self._conn(autocommit=False) as conn:
            cursor = conn.cursor()
            for query, params in queries:
                cursor.execute(query, params)
            conn.commit()
            return True

    @api.model
    def _execute_read(self, query, params=None, size=1000):
        with self._conn() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            while True:
                data = cursor.fetchmany(size)
                yield data
                if not data:
                    break
