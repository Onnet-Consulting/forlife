# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.addons.forlife_redis_integration.models.integration_redis import declare_redis_action_key

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'redis.action']

    @declare_redis_action_key('send_order_tkl')
    def toggle_active(self):
        self.set_redis_value('test_data', 'ok baby')
        return super().toggle_active()


