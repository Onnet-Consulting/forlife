# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AssetsAssets(models.Model):
    _inherit = 'assets.assets'

    bravo_create_date = fields.Datetime(
        readonly=True,
        help='This datetime will be save in database in UTC+7 format - timezone (Asia/Ho_Chi_Minh)\n'
             'This value is synchronized between bravo and Odoo, not by normal Odoo action \n'
             'so the datetime will not be convert to UTC value like normally')
