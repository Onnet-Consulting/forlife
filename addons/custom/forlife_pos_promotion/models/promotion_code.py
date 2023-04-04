# -*- coding: utf-8 -*-
from uuid import uuid4

from odoo import models, fields, api


class PromotionCode(models.Model):
    _name = 'promotion.code'
    _description = 'Promotion Code'
    _rec_name = 'name'

    @api.model
    def _generate_code(self):
        """
        Barcode identifiable codes.
        """
        return '044' + str(uuid4())[7:-18]

    program_id = fields.Many2one('promotion.program', ondelete='cascade')
    name = fields.Char(default=lambda self: self._generate_code(), required=True)
    partner_id = fields.Many2one('res.partner')
    used_partner_ids = fields.Many2many('res.partner', 'promotion_code_used_res_partner_rel', readonly=True)
    # Nếu được gán Partner thì dùng 1 lần duy nhất
    # Nếu không gán Partner thì dùng được nhiều lần dựa trên giới hạn sử dụng

    limit_usage = fields.Boolean(related='program_id.limit_usage')
    max_usage = fields.Integer()

    amount = fields.Float()
    consumed_amount = fields.Float()
    remaining_amount = fields.Float(compute='_compute_remaining_amount', store=False)
    reward_for_referring = fields.Boolean('Rewards for Referring', copy=False, readonly=False)
    referring_date_from = fields.Datetime('Refer From')
    referring_date_to = fields.Datetime('Refer To')
    referring_program_id = fields.Many2one('promotion.program', string='Program Reward')

    referred_partner_id = fields.Many2one('res.partner')
    expiration_date = fields.Datetime()

    usage_line_ids = fields.One2many('promotion.usage.line', 'code_id')
    use_count = fields.Integer(compute='_compute_use_count_order', string='Number of Order Usage')
    order_ids = fields.Many2many('pos.order', compute='_compute_use_count_order', string='Order')

    def _compute_use_count_order(self):
        for code in self:
            order_ids = code.usage_line_ids.mapped('order_line_id.order_id')
            code.order_ids = order_ids
            code.use_count = len(order_ids)

    @api.depends('amount', 'consumed_amount')
    def _compute_remaining_amount(self):
        for code in self:
            code.remaining_amount = code.amount - code.consumed_amount