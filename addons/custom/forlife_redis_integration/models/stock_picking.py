# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'redis.action']

    def create(self, vals_list):
        res = super(StockPicking, self).create(vals_list)
        for picking in res.filtered(lambda x: x.picking_type_code == 'internal'):
            # FIXME: send data with correct key (TKL or FM)
            self.hset('internal_transfer', 'Invoice', picking.name, {"InvoiceNo": picking.id})
        return res
