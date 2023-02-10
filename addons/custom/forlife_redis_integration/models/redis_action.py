# -*- coding:utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import MissingError

import redis


class RedisAction(models.AbstractModel):
    _name = 'redis.action'
    _description = 'If a model needs to send data to Redis, it need to inherit redis.action'

    def _conn(self, action_key):
        redis_action_key = self.env['redis.action.key'].search([('key', '=', action_key)])
        rds_host = redis_action_key.host_id
        if not rds_host:
            raise MissingError(
                _("An Redis action key name '%s' is missing or \
                 there are no Redis host attached to that key") % action_key)

        return redis.Redis(host=rds_host.host, port=rds_host.port,
                           db=rds_host.db, password=rds_host.password, username=rds_host.username)

    @api.model
    def hset(self, action_key, hash_name, key, value):
        conn = self._conn(action_key)
        conn.hset(hash_name, key, value)
