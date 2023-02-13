# -*- coding: utf-8 -*-

from odoo import models, fields


class PosPromotionLine(models.Model):
    _name = 'promotion.usage.line'
    _description = 'Promotion Usage Line'

    order_line_id = fields.Many2one('pos.order.line')
    program_id = fields.Many2one('promotion.program')
    discount_amount = fields.Float('Discount Amount')


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    promotion_usage_ids = fields.One2many('promotion.usage.line', 'order_line_id')
