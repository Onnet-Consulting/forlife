# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Brand(models.Model):
    _name = 'brand'
    _description = 'Brand'

    name = fields.Char('Name', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Brand name must be unique !'),
    ]
