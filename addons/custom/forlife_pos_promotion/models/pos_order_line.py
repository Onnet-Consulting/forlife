# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo import tools


class PosPromotionLine(models.Model):
    _name = 'promotion.usage.line'
    _description = 'Promotion Usage Line'

    order_line_id = fields.Many2one('pos.order.line', readonly=True)
    order_id = fields.Many2one(related='order_line_id.order_id', store=True)
    program_id = fields.Many2one('promotion.program', readonly=True, ondelete='restrict')
    discount_amount = fields.Float('Discount Amount', readonly=True)
    code_id = fields.Many2one('promotion.code', readonly=True)
    original_price = fields.Float('Original Price', readonly=True)
    new_price = fields.Float('New Price', readonly=True)

    def name_get(self):
        res = []
        for line in self:
            name = _('Discount ') \
                    + tools.format_amount(self.env, line.discount_amount, line.order_line_id.order_id.currency_id) \
                    + _(' of ') + line.program_id.name
            res += [(line.id, name)]
        return res


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    promotion_usage_ids = fields.One2many('promotion.usage.line', 'order_line_id')
