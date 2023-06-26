# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _description = 'Delivery Carrier'

    nhanh_id = fields.Integer('Nhanh Id')
    name = fields.Char('Name')
    code = fields.Char('Code')
    service_name = fields.Char('Service Name')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Delivery Carrier name already exists !"),
        ('nhanh_id_uniq', 'unique (nhanh_id)', "Delivery Carrier Nhanh Id already exists !")
    ]
