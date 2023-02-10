# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.addons.forlife_redis_integration.models.api import declare_redis_action_key


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'redis.action']

    @declare_redis_action_key(['show1', 'show2'])
    def toggle_active(self):
        res = super().toggle_active()
        self.redis_conn('show1').set('from', 'server #1')
        self.redis_conn('show2').hset('Planets Universe', 'moon', 'cool')
        return res
