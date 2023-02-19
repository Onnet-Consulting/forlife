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

    program_id = fields.Many2one('promotion.program')
    name = fields.Char(default=lambda self: self._generate_code(), required=True)
    partner_id = fields.Many2one('res.partner')
    used_partner_ids = fields.Many2many('res.partner', 'promotion_code_used_res_partner_rel')
    # Nếu được gán Partner thì dùng 1 lần duy nhất
    # Nếu không gán Partner thì dùng được nhiều lần dựa trên giới hạn sử dụng

    limit_usage = fields.Boolean(related='program_id.limit_usage', store=True)
    max_usage = fields.Integer(related='program_id.max_usage', store=True)
    num_of_usage = fields.Integer('Number of usage')

    amount = fields.Float()
    consumed_amount = fields.Float()
    remaining_amount = fields.Float()
    pos_order_ids = fields.Many2many('pos.order')
    reward_for_referring = fields.Boolean(related='program_id.reward_for_referring')
    referred_partner_id = fields.Many2one('res.partner')
    expiration_date = fields.Date()
    use_count = fields.Integer(compute='_compute_use_count')

    def _compute_use_count(self):
        self.use_count = 0
        for code in self:
            self.use_count = self.env['promotion.usage.line'].search(
                ['code_id', '=', code.id]).mapped('order_line_id.order_id')
