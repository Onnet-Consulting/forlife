# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo import tools


class PosPromotionLine(models.Model):
    _name = 'promotion.usage.line'
    _description = 'Promotion Usage Line'

    order_line_id = fields.Many2one('pos.order.line', readonly=True)
    order_id = fields.Many2one(related='order_line_id.order_id', store=True)
    program_id = fields.Many2one('promotion.program', readonly=True, ondelete='restrict')
    currency_id = fields.Many2one(related='order_id.currency_id')
    discount_amount = fields.Float('Discount Price', readonly=True)
    code_id = fields.Many2one('promotion.code', readonly=True, ondelete='restrict')
    pro_priceitem_id = fields.Many2one('promotion.pricelist.item', readonly=True, ondelete='restrict')
    str_id = fields.Char(readonly=True)
    original_price = fields.Float('Original Price', readonly=True)
    new_price = fields.Float('New Price', readonly=True)
    qty = fields.Float('Quantity', related='order_line_id.qty', digits='Product Unit of Measure')
    discount_total = fields.Monetary('Discount Amount', readonly=True, compute='_compute_discount_total')

    discount_based_on = fields.Char()
    promotion_type = fields.Char()
    registering_tax = fields.Boolean(readonly=True)
    program_from_date = fields.Datetime(related='program_id.from_date', string='Từ ngày')
    program_to_date = fields.Datetime(related='program_id.to_date', string='Đến ngày')

    def name_get(self):
        res = []
        for line in self:
            name = _('Discount ') \
                    + tools.format_amount(self.env, line.discount_amount, line.order_line_id.order_id.currency_id) \
                    + _(' of ') + line.program_id.name
            res += [(line.id, name)]
        return res

    def _compute_discount_total(self):
        for line in self:
            line.discount_total = line.qty*line.discount_amount


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    promotion_usage_ids = fields.One2many('promotion.usage.line', 'order_line_id')
    original_price = fields.Float('Original Price', digits=0, default=0)
    is_reward_line = fields.Boolean('Is Reward Line')
