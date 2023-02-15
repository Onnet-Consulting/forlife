# -*- coding:utf-8 -*-

from odoo import fields, models


class RedisActionKey(models.Model):
    _name = 'redis.action.key'
    _description = 'Redis Action Key'
    _rec_name = 'key'

    key = fields.Char(string='Key', required=True,
                      help='A key identify a specific Odoo action need to send data to Redis', )
    description = fields.Text(string='Description')
    host_id = fields.Many2one('redis.host', string='Host', ondelete="restrict")

    _sql_constraints = [
        ('unique_key', 'UNIQUE(key)', 'The action key must be unique !')
    ]
