# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class PromotionVoucher(models.Model):
    _name = 'promotion.voucher'
    _description = 'Voucher'

    name = fields.Char()
    program_id = fields.Many2one('promotion.program')
