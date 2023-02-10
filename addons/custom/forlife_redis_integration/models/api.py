# -*- coding:utf-8 -*-

import functools


def declare_redis_action_key(action_keys):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self = args[0]
            if type(action_keys) is str:
                keys = [action_keys]
            else:
                keys = action_keys.copy()
            self = self.with_context(redis_action_keys=self.env['redis.action.key'].search([('key', 'in', keys)]).ids)
            # self.key_ids = self.env['redis.action.key'].search([('key', 'in', keys)]).ids
            return func(*args, **kwargs)

        return wrapper

    return decorator
