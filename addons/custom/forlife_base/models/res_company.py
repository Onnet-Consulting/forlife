# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    code = fields.Char(string='Code')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Company code must be unique!')
    ]
