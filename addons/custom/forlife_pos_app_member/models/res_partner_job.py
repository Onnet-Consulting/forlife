# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartnerJob(models.Model):
    _name = 'res.partner.job'
    _description = 'Job'

    name = fields.Char(string='Name')

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Job name already exists!')
    ]
