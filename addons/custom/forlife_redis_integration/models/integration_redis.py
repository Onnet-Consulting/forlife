# -*- coding:utf-8 -*-

from odoo import api, fields, models
import redis

import functools


class RedisHost(models.Model):
    _name = 'redis.host'

    host = fields.Char(string='Host', default='localhost', required=True)
    username = fields.Char(string='Username', default='default', required=True)
    password = fields.Char(string='Password', default=False, required=True)
    port = fields.Integer(string='Port', default=6379, required=True)
    db = fields.Char(string='Database', default=0, required=True)
    key_ids = fields.One2many('redis.action.key', 'host_id')

    @property
    def _conn(self):
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


class RedisActionKey(models.Model):
    _name = 'redis.action.key'
    _rec_name = 'key'

    # FIXME: add constraint to key to be unique
    key = fields.Char(help='A key identify a specific Odoo action need to send data to Redis', )
    description = fields.Text()
    host_id = fields.Many2one('redis.host')


class RedisAction(models.AbstractModel):
    _name = 'redis.action'
    _description = 'If a model needs to send data to Redis, it need to have a redis.action instance'

    key_ids = fields.Many2many('redis.action.key', string='Action Key')

    @property
    def conn(self):
        rds_host = self.env['redis.action.key'].search([('key', '=', self.action_key)]).host_id
        return redis.Redis(host=rds_host.host, port=rds_host.port,
                           db=rds_host.db, password=rds_host.password, username=rds_host.username)

    def set_redis_value(self, key, value, **kwargs):
        conn = self.conn
        conn.set(key, value)


def declare_redis_action_key(action_keys):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self = args[0]
            self.key_ids = self.env['redis.action.key'].search([('key', 'in', action_keys)])
            return func(*args, **kwargs)

        return wrapper

    return decorator
