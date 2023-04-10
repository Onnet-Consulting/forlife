# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.convert import safe_eval


class PromotionGenerateCode(models.Model):
    _name = 'promotion.generate.code'
    _description = 'Promotion Generate Code'

    program_id = fields.Many2one(
        'promotion.program', default=lambda self: self.env.context.get('active_id'))
    customer_domain = fields.Char(related='program_id.customer_domain')
    mode = fields.Selection([
        ('anonymous', 'Anonymous Customers'),
        ('selected', 'Selected Customers')],
        string='For', compute='_compute_mode'
    )
    valid_until = fields.Date()
    coupon_qty = fields.Integer(
        'Quantity', compute='_compute_coupon_qty', readonly=False, store=True)
    reward_for_referring = fields.Boolean('Rewards for Referring', copy=False, readonly=False, default=False)
    referring_date_from = fields.Datetime('Refer Date From')
    referring_date_to = fields.Datetime('Refer Date To')
    reward_program_id = fields.Many2one('promotion.program', string='Referring Program Reward')

    promotion_type = fields.Selection(related='program_id.promotion_type')

    limit_usage = fields.Boolean(string='Limit usage', related='program_id.limit_usage')
    max_usage = fields.Integer(string='Max usage per Code')

    @api.depends('program_id', 'program_id.customer_domain')
    def _compute_mode(self):
        for wizard in self:
            if wizard.program_id.customer_domain in ['[]', False]:
                wizard.mode = 'anonymous'
            else:
                wizard.mode = 'selected'

    def _get_partners(self):
        self.ensure_one()
        if self.mode != 'selected':
            return self.env['res.partner']
        domain = safe_eval(self.customer_domain or "[('id', '=', 0)]")
        return self.env['res.partner'].search(domain)

    @api.depends('customer_domain', 'mode')
    def _compute_coupon_qty(self):
        for wizard in self:
            if wizard.mode == 'selected':
                wizard.coupon_qty = len(wizard._get_partners())
            else:
                wizard.coupon_qty = wizard.coupon_qty or 0

    def _get_coupon_values(self, partner, force_partner=False):
        self.ensure_one()
        program = self.program_id
        if program.reward_type in ('combo_amount', 'code_amount'):
            amount = program.disc_amount
        elif program.reward_type == 'code_percent':
            amount = program.disc_max_amount
        else:
            amount = 0.0
        result = {
            'program_id': self.program_id.id,
            'amount': amount,
            'partner_id': partner.id if self.mode == 'selected' or force_partner else False,
            'expiration_date': self.valid_until or self.program_id.to_date or False,
            'max_usage': self.max_usage
        }
        if self.reward_for_referring:
            result['reward_for_referring'] = self.reward_for_referring
            result['referring_date_from'] = self.referring_date_from
            result['referring_date_to'] = self.referring_date_to
            result['reward_program_id'] = self.reward_program_id.id
        return result

    @api.onchange('program_id')
    def onchange_program_id(self):
        if self.program_id.limit_usage:
            self.max_usage = self.program_id.max_usage

    @api.onchange('referring_date_from', 'referring_date_to')
    def onchange_referring_date_valid(self):
        if self.referring_date_from and self.referring_date_to and self.referring_date_from > self.referring_date_to:
            raise UserError(_('Ngày bắt đầu phải nhỏ hơn ngày kết thúc!'))

    def generate_codes(self):
        if any(not wizard.program_id for wizard in self):
            raise ValidationError(_("Can not generate code, no program is set."))
        if any(wizard.coupon_qty <= 0 for wizard in self):
            raise ValidationError(_("Invalid quantity."))
        code_create_vals = []
        for wizard in self:
            customers = wizard._get_partners() or range(wizard.coupon_qty)
            for partner in customers:
                code_create_vals.append(wizard._get_coupon_values(partner))
        self.env['promotion.code'].create(code_create_vals)
        return True
