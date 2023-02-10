# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.addons.forlife_redis_integration.models.api import declare_redis_action_key


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'redis.action']

    @declare_redis_action_key('send_partner')
    def toggle_active(self):
        res = super().toggle_active()
        self.redis_conn('send_partner').set('data', self.name)
        return res
