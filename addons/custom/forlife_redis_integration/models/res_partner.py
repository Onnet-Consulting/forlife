# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.addons.forlife_redis_integration.models.api import declare_redis_action_key

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'redis.action']

    @declare_redis_action_key('send_order_tkl')
    def toggle_active(self):
        self.redis_conn('send_order_tkl').set('test_data', 'ok baby')
        return super().toggle_active()



class x(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'redis.action']

    @declare_redis_action_key(['show1', 'show2'])
    def toggle_active(self):
        res = super().toggle_active()
        self.redis_conn('show1').set('hehe', 'ezzzzzz')
        self.redis_conn('show2').hset('Plannets Universe', 'sun', 'so hot bro, dont touch it')
        return res