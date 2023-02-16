# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.osv.expression import OR


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_promotion_program_ids(self):
        return self.env['promotion.program'].search(
            [('state', '=', 'in_progress'), '|', ('pos_config_ids', '=', self.id), ('pos_config_ids', '=', False)])

    def use_promotion_code(self, code, creation_date, partner_id):
        self.ensure_one()
        # Ordering by partner id to use the first assigned to the partner in case multiple coupons have the same code
        #  it could happen with loyalty programs using a code
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
        check_date = fields.Date.from_string(creation_date[:11])
        if (code_id.expiration_date and code_id.expiration_date < check_date) or\
            (code_id.program_id.to_date and code_id.program_id.to_date < fields.Datetime.now()) or\
            (code_id.program_id.limit_usage and code_id.program_id.total_order_count >= code_id.program_id.max_usage):
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
            },
        }
