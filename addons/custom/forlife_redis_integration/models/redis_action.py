# -*- coding:utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import MissingError

import redis


class RedisAction(models.AbstractModel):
    _name = 'redis.action'
    _description = 'If a model needs to send data to Redis, it need to have a redis.action instance'

    key_ids = fields.Many2many('redis.action.key', string='Action Key')

    def redis_conn(self, action_key):
        # search key
        redis_action_keys = self._context.get('redis_action_keys')
        if not redis_action_keys:
            raise MissingError(_("Use must execute redis action with context key 'redis_action_keys'"))
        redis_action_keys = self.env['redis.action.key'].browse(redis_action_keys)
        action_key_instance = redis_action_keys.filtered(lambda x: x.key == action_key)
        rds_host = action_key_instance.host_id
        if not rds_host:
            raise MissingError(
                _("An Redis action key name '%s' is missing or there are no Redis host attached to it") % action_key)

        return redis.Redis(host=rds_host.host, port=rds_host.port,
                           db=rds_host.db, password=rds_host.password, username=rds_host.username)

    def hset(self, action_key, hash_name, key, value):
        conn = self.redis_conn(action_key)
        conn.hset(hash_name, key, value)
