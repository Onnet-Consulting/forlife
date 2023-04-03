# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StoreFirstOrder(models.Model):
    _name = 'store.first.order'
    _description = 'Store First Order'
    _order = 'customer_id, brand_id, store_id'
    _rec_name = 'customer_id'

    customer_id = fields.Many2one("res.partner", string="Customer", required=True, ondelete='restrict')
    brand_id = fields.Many2one("res.brand", string="Brand", required=True)
    store_id = fields.Many2one("store", string="Store", required=True)

    _sql_constraints = [
        ('data_uniq', 'unique (customer_id, brand_id)', 'Brand on Customer must be unique !'),
    ]
