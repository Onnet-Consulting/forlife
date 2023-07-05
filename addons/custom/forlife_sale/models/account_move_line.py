# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_product_code_id = fields.Many2one('assets.assets', string='Mã tài sản')
