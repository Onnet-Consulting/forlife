# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import json


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'redis.action']

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockPicking, self).create(vals_list)
        res.with_delay(max_retries=10).send_new_internal_transfer()
        return res

    def send_new_internal_transfer(self):
        for picking in self.filtered(lambda x: x.picking_type_code == 'internal'):
            # FIXME: send data with correct key (TKL or FM)
            self.hset('internal_transfer', 'Invoice', picking.name, json.dumps({"InvoiceNo": picking.id}))
