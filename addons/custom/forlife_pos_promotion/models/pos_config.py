# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.osv.expression import OR


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_promotion_program_ids(self):
        return self.env['promotion.program'].search(
            [('state', '=', 'in_progress'), '|', ('campaign_id.store_ids', '=', False), ('campaign_id.store_ids', '=', self.store_id.id)])

    def get_history_program_usages(self, partner_id: int, programs: list):
        """"""
        programs = [int(p) for p in programs]
        usages = self.env['promotion.usage.line'].search([
            ('order_id.partner_id', '=', partner_id),
            ('program_id', 'in', programs)
        ])
        result = dict()
        programs = {key: 0 for key in programs}
        for usage in usages:
            programs[usage.program_id.id] += usage.order_line_id.qty
        for (program_id, qty) in programs.items():
            program = self.env['promotion.program'].browse(program_id)
            applied_number = qty/program.qty_per_combo \
                if program.promotion_type == 'combo' and program.qty_per_combo > 0 else qty
            result[program_id] = applied_number
        return result

    def use_promotion_code(self, code, creation_date, partner_id):
        self.ensure_one()
        code_id = self.env['promotion.code'].search(
            [('program_id', 'in', self._get_promotion_program_ids().ids), ('partner_id', 'in', (False, partner_id)), ('name', '=', code)],
            order='partner_id', limit=1)

        if not code_id or not code_id.program_id.active:
            return {
                'successful': False,
                'payload': {
                    'error_message': _('This coupon is invalid (%s).', code),
                },
            }
        check_date = fields.Datetime.from_string(creation_date.replace('T', ' ')[:19])
        if (code_id.expiration_date and code_id.expiration_date < check_date) or\
            (code_id.program_id.to_date and code_id.program_id.to_date < check_date) or\
            (code_id.limit_usage and code_id.use_count >= code_id.max_usage):
            return {
                'successful': False,
                'payload': {
                    'error_message': _('This coupon is expired (%s).', code),
                },
            }
        return {
            'successful': True,
            'payload': {
                'program_id': code_id.program_id.id,
                'code_id': code_id.id,
                'coupon_partner_id': code_id.partner_id.id,
                'remaining_amount': code_id.remaining_amount,
            },
        }
