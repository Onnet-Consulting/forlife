# -*- coding:utf-8 -*-

from odoo import api, fields, models
import redis


class IntegrationRedis(models.Model):
    _name = 'integration.redis'

    host = fields.Char(string='Host', default='localhost', required=True)
    username = fields.Char(string='Username', default='default', required=True)
    password = fields.Char(string='Password', default=False, required=True)
    port = fields.Integer(string='Port', default=6379, required=True)
    db = fields.Char(string='Database', default=0, required=True)
    connection_key = fields.Char(string='Connection Key', help="Key used to identify redis server")

    @property
    def _redis_con(self):
        return redis.Redis(host=self.host, port=self.port, db=self.db, password=self.password, username=self.username)


    def get_connection(self):
        self.ensure_one()
        conn = redis.Redis(host=self.host, port=self.port, db=self.db, password=self.password, username=self.username)
        return conn

    def set_value(self, key, value, **kwargs):
        conn = self.get_connection()
        conn.set(key, value)

    def get_value(self, key, **kwargs):
        conn = self.get_connection()
        return conn.get(key)

    # def execute_command(self, *args, **kwargs):
    #     command_name = args[0]

