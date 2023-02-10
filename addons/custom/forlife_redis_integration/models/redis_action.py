# -*- coding:utf-8 -*-

from odoo import fields, models
import redis


class RedisAction(models.AbstractModel):
    _name = 'redis.action'
    _description = 'If a model needs to send data to Redis, it need to have a redis.action instance'

    key_ids = fields.Many2many('redis.action.key', string='Action Key')

    def redis_conn(self, action_key):
        action_key_instance = self.key_ids.filtered(lambda x: x.key == action_key)
        if not action_key_instance:
            # FIXME: should we raise error when no redis host found
            return False
        rds_host = action_key_instance.host_id
        return redis.Redis(host=rds_host.host, port=rds_host.port,
                           db=rds_host.db, password=rds_host.password, username=rds_host.username)
