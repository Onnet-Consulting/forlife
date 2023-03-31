# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class Store(models.Model):
    _inherit = 'store'

    number_month = fields.Integer('Number Month')
