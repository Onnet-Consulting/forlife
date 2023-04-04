# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class VoucherVoucher(models.Model):
    _inherit = 'voucher.voucher'

    promotion_program_id = fields.Many2one('promotion.program', string='Promotion Program Ref', readonly=True)
    orig_pos_order_id = fields.Many2one('pos.order', 'Original POS Order', readonly=True)
