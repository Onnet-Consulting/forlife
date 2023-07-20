# -*- coding: utf-8 -*-
from ast import literal_eval
from itertools import groupby

from odoo import models, fields, _
from odoo.osv.expression import OR


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_promotion_campaign_ids(self):
        return self.env['promotion.campaign'].search(
            [('state', '=', 'in_progress'), '|', ('store_ids', '=', False),
             ('store_ids', '=', self.store_id.id)])

    def _get_promotion_program_ids(self):
        return self.env['promotion.program'].search(
            [('state', '=', 'in_progress'), '|', ('campaign_id.store_ids', '=', False),
             ('campaign_id.store_ids', '=', self.store_id.id)])

    def get_history_program_usages(self, partner_id: int, programs: list):
        """"""
        programs = [int(p) for p in programs]
        input_program_ids = self.env['promotion.program'].browse(programs)
        usages = self.env['promotion.usage.line'].search([
            ('order_id.partner_id', '=', partner_id),
            ('program_id', 'in', programs)
        ])
        result = dict()
        no_active_programs = []
        value_programs = {key: 0 for key in programs}
        for usage in usages:
            value_programs[usage.program_id.id] += usage.order_line_id.qty
        for (program_id, qty) in value_programs.items():
            program = self.env['promotion.program'].browse(program_id)
            if not program.exists():
                no_active_programs.append(program_id)
            else:
                if program.promotion_type in ['code', 'cart', 'pricelist']:
                    applied_number = len(usages.filtered(lambda u: u.program_id.id == program_id).mapped('order_id'))
                else:
                    applied_number = qty / program.qty_per_combo if program.qty_per_combo > 0 else qty
                result[program_id] = applied_number

        # Get history limit qty per program
        combo_program_ids = input_program_ids.filtered(lambda p: p.exists() and p.limit_usage_per_program)
        limited_program_usages = self.env['promotion.usage.line'].search([('program_id', 'in', combo_program_ids.ids)])
        all_usage_promotions = {}
        for program in combo_program_ids:
            usages = limited_program_usages.filtered(lambda u: u.program_id.id == program.id)
            if program.promotion_type == 'combo':
                qty = sum([usage.order_line_id.qty for usage in usages])
                applied_number = qty / program.qty_per_combo if program.qty_per_combo > 0 else qty
            else:
                applied_number = len(usages.mapped('order_id'))
            all_usage_promotions[program.id] = applied_number
        result['all_usage_promotions'] = all_usage_promotions
        result['no_active_programs'] = no_active_programs
        return result

    def load_promotion_valid_new_partner(self, partner_id, promotion_programs):
        if len(promotion_programs) == 0:
            return []
        if not (isinstance(promotion_programs, list) and all([el.isdigit() for el in promotion_programs])):
            return []
        partner = self.env['res.partner'].sudo().browse(partner_id)
        result = []
        self.env.cr.execute("SELECT id,customer_domain FROM promotion_program "
                            "WHERE id IN %(promotion_programs)s AND active = true AND state = 'in_progress'",
                            {'promotion_programs': tuple(promotion_programs)})
        existed = self.env.cr.dictfetchall()
        existed_customer_domain = {str(p['id']): p['customer_domain'] for p in existed}
        for program_id in promotion_programs:
            if program_id in existed_customer_domain.keys() and partner.filtered_domain(literal_eval(existed_customer_domain[program_id])):
                result.append(program_id)
        return result

    def update_surprising_program(self, lines):
        result = {}
        line_rewards = self.env['surprising.reward.product.line'].browse(lines)
        for line in line_rewards:
            result[line.id] = line.issued_qty
        return result

    def use_promotion_code(self, code, creation_date, partner_id):
        self.ensure_one()
        code_id = self.env['promotion.code'].search(
            [('program_id', 'in', self._get_promotion_program_ids().ids),
             ('name', '=', code),
             '|',
             ('partner_id', 'in', (False, partner_id)),
             ('reward_for_referring', '=', True)
             ],
            order='partner_id', limit=1)

        if not code_id or not code_id.program_id.active:
            return {
                'successful': False,
                'payload': {
                    'error_message': _('This coupon is invalid (%s).', code),
                },
            }
        check_date = fields.Datetime.from_string(creation_date.replace('T', ' ')[:19])
        if (code_id.expiration_date and code_id.expiration_date < check_date) or \
                (code_id.program_id.to_date and code_id.program_id.to_date < check_date) or \
                (code_id.limit_usage and code_id.use_count >= code_id.max_usage) or \
                (code_id.program_id.reward_type == 'code_amount' and code_id.remaining_amount <= 0.0):
            return {
                'successful': False,
                'payload': {
                    'error_message': _('This coupon is expired or over maximum usages: (%s).', code),
                },
            }

        history = {}
        if code_id.program_id.limit_usage_per_customer:
            history = self.get_history_program_usages(partner_id, [code_id.program_id.id])
            if history.get(code_id.program_id.id, 0) >= code_id.program_id.max_usage_per_customer:
                return {
                    'successful': False,
                    'payload': {
                        'error_message': _('This coupon is expired or over maximum usages: (%s).', code),
                    },
                }
        if code_id.program_id.limit_usage_per_program:
            history = history or self.get_history_program_usages(partner_id, [code_id.program_id.id])
            if history.get('all_usage_promotions', {}).get(code_id.program_id.id, 0) >= code_id.program_id.max_usage_per_program:
                return {
                    'successful': False,
                    'payload': {
                        'error_message': _('This coupon is expired or over maximum usages: (%s).', code),
                    },
                }

        has_reward = False
        if code_id.reward_for_referring:
            order_partner = self.env['res.partner'].browse(partner_id)
            code_partner = code_id.partner_id
            is_new_customer = not order_partner.sudo().store_fo_ids.filtered(
                lambda r: r.brand_id == code_id.program_id.brand_id)
            valid_date = code_id.referring_date_from <= check_date <= code_id.referring_date_to
            has_reward = bool(order_partner and code_partner and order_partner.id != code_partner.id and is_new_customer and valid_date)
        return {
            'successful': True,
            'payload': {
                'program_id': code_id.program_id.id,
                'code_id': code_id.id,
                'coupon_partner_id': code_id.partner_id.id,
                'remaining_amount': code_id.remaining_amount,
                'reward_for_referring': has_reward,
                'reward_program_id': has_reward and code_id.reward_program_id.id,
                'reward_program_name': code_id.reward_program_id.name or ''
            },
        }
