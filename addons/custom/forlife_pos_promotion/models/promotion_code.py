# -*- coding: utf-8 -*-
import random
import unicodedata
from uuid import uuid4
import requests

from odoo import models, fields, api, _


class PromotionCode(models.Model):
    _inherit = ['mail.thread']
    _name = 'promotion.code'
    _description = 'Promotion Code'
    _rec_name = 'name'

    def _get_code(self):
        letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789'
        code = ''.join(random.choices(letters, k=8))
        if self.env['promotion.code'].search([('name', 'like', code)]):
            self._get_code()
        else:
            return code

    @api.depends('program_id')
    def _compute_code(self):
        for code in self:
            code.name = str(code.program_id.id) + '-' + self._get_code()

    program_id = fields.Many2one('promotion.program', ondelete='cascade')
    name = fields.Char(compute='_compute_code', store=True, readonly=False, tracking=True)
    partner_id = fields.Many2one('res.partner')
    used_partner_ids = fields.Many2many('res.partner', 'promotion_code_used_res_partner_rel', readonly=True)
    # Nếu được gán Partner thì dùng 1 lần duy nhất
    # Nếu không gán Partner thì dùng được nhiều lần dựa trên giới hạn sử dụng

    limit_usage = fields.Boolean(related='program_id.limit_usage')
    max_usage = fields.Integer(tracking=True)

    amount = fields.Float(tracking=True)
    consumed_amount = fields.Float(tracking=True)
    remaining_amount = fields.Float(compute='_compute_remaining_amount', store=False)
    reward_for_referring = fields.Boolean('Reward for Referring', copy=False, readonly=False)
    referring_date_from = fields.Datetime('Refer From', tracking=True)
    referring_date_to = fields.Datetime('Refer To', tracking=True)
    reward_program_id = fields.Many2one('promotion.program', string='Program Reward')
    original_program_id = fields.Many2one('promotion.program', string='Original Program', readonly=True)
    original_order_id = fields.Many2one('pos.order', 'Original Order', readonly=True)
    original_code_id = fields.Many2one('promotion.code', string='Original Code')
    reward_code_ids = fields.One2many('promotion.code', 'original_code_id', string='Reward Codes')
    issued_code_quantity = fields.Integer(compute='_compute_issued_code_quantity')
    surprising_reward_line_id = fields.Many2one('surprising.reward.product.line', readonly=True)

    referred_partner_id = fields.Many2one('res.partner')
    expiration_date = fields.Datetime()

    usage_line_ids = fields.One2many('promotion.usage.line', 'code_id')
    use_count = fields.Integer(compute='_compute_use_count_order', string='Number of Order Usage')
    order_ids = fields.Many2many('pos.order', compute='_compute_use_count_order', string='Order')

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.name = unicodedata.normalize('NFKD', self.name.upper()).encode('ascii', 'ignore')

    def _compute_use_count_order(self):
        for code in self:
            order_ids = code.usage_line_ids.mapped('order_line_id.order_id')
            code.order_ids = order_ids
            code.use_count = len(order_ids)

    def _compute_issued_code_quantity(self):
        for code in self:
            code.issued_code_quantity = len(code.reward_code_ids)

    @api.depends('amount', 'consumed_amount')
    def _compute_remaining_amount(self):
        for code in self:
            code.remaining_amount = max(0.0, code.amount - code.consumed_amount)

    def action_open_promotion_codes(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id("forlife_pos_promotion.promotion_code_card_action")
        action['name'] = _('Promotion Code: ') + self.name
        action['display_name'] = action['name']
        action['context'] = {
            'create': 0,
            'edit': 0,
        }
        action['domain'] = [('id', 'in', self.reward_code_ids.ids)]
        return action

    @api.model_create_multi
    def create(self, values):
        res = super().create(values)
        codes = res.filtered(lambda f: f.partner_id)
        if codes:
            codes.sudo().with_delay(description="GỬI NOTIFICATION MÃ CODE TẶNG CHO KHÁCH HÀNG").push_notification_to_app()
        return res

    def push_notification_to_app(self):
        app_api_link = {}
        for l in self.env['forlife.app.api.link'].search([]):
            app_api_link.update({l.key: l.value})
        for c in self:
            try:
                link = app_api_link.get(c.program_id.brand_id.code)
                if link:
                    param = f'type=pushNotificationVIP&id={c.program_id.notification_id}&voucher={c.name}&gift=&customerId={c.partner_id.phone}'
                    requests.get(link + param)
            except:
                pass
