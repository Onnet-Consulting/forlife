# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_redis_integration.models.api import declare_redis_action_key


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'redis.action']

    @declare_redis_action_key('internal_transfer')
    def create(self, vals_list):
        res = super(StockPicking, self).create(vals_list)
        for picking in res.filtered(lambda x: x.picking_type_code == 'internal'):
            self.hset('internal_transfer', 'Invoice', picking.name, {"InvoiceNo": picking.id})
        return res
