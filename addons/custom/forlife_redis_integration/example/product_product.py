# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'redis.action']

    def create(self, vals_list):
        res = super(ProductProduct, self).create(vals_list)
        self.redis_conn('show1').set('from', 'server #1')
        self.redis_conn('show2').hset('Planets Universe', 'moon', 'cool')
        return res
