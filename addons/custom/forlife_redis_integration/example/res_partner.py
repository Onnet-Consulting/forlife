# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'redis.action']

    def toggle_active(self):
        res = super().toggle_active()
        self.redis_conn('send_partner').set('data', self.name)
        return res
