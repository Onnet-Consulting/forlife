# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResBrand(models.Model):
    _name = 'res.brand'
    _description = 'Brand'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'Brand code must be unique !'),
    ]
