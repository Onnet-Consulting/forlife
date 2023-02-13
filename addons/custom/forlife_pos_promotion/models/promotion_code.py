# -*- coding: utf-8 -*-

from odoo import models, fields


class PromotionCode(models.Model):
    _name = 'promotion.code'
    _description = 'Promotion Code'
    _rec_name = 'name'

    program_id = fields.Many2one('promotion.program')
    name = fields.Char()
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
