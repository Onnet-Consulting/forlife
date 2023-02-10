# -*- coding:utf-8 -*-

from odoo import fields, models


class RedisHost(models.Model):
    _name = 'redis.host'
    _description = 'Redis Host'

    host = fields.Char(string='Host', default='localhost', required=True)
    username = fields.Char(string='Username', default='default')
    password = fields.Char(string='Password', default=False)
    port = fields.Integer(string='Port', default=6379, required=True)
    db = fields.Char(string='Database', default=0, required=True)
    key_ids = fields.One2many('redis.action.key', 'host_id', string='Action Keys')
