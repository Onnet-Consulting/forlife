from odoo import api, fields, models,_
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_payment_method(self):
        res = super(PosSession, self)._loader_params_pos_payment_method()
        data = res['search_params']['fields']
        data.append('is_voucher')
        res['search_params']['fields'] = data
        return res

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super(PosSession, self).action_pos_session_closing_control(balancing_account, amount_to_balance, bank_payment_method_diffs)
        for session in self:
            vouchers = session.order_ids.pos_voucher_line_ids.filtered(lambda v: v.voucher_id.purpose_id.purpose_voucher == 'gift')
            department_ids = []
            if vouchers:
                for v in vouchers:
                    department_ids.append(v.derpartment_id)
                for d in department_ids:
                    vouchers_follow_department = vouchers.filtered(lambda v: v.derpartment_id.id == d.id)
                    session.create_jn_entry_voucher_gift(vouchers_follow_department, d)
        return res

    def create_jn_entry_voucher_gift(self, vouchers, d):
        payment_mothod = self.env['pos.payment.method'].search([('is_voucher', '=', True), ('company_id', '=', self.env.company.id)], limit=1)
        AccountMove = self.env['account.move']
        if payment_mothod and payment_mothod.account_other_income and payment_mothod.account_other_fee:
            move_vals = {
                'ref': 'Hạch toán voucher tặng',
                'date': datetime.now(),
                'journal_id': payment_mothod.journal_id.id,
                'company_id': payment_mothod.company_id.id,
                'move_type': 'entry',
                'ss_id': self.id,
                'line_ids': [
                    # credit line
                    (0, 0, {
                        'name': vouchers[0].pos_order_id.name,
                        'display_type': 'product',
                        'account_id': payment_mothod.account_other_income.id,
                        'debit': 0.0,
                        'credit': sum(vouchers.mapped('price_used')),
                    }),
                    # debit line
                    (0, 0, {
                        'name': vouchers[0].pos_order_id.name,
                        'display_type': 'product',
                        'account_id': payment_mothod.account_other_fee.id,
                        'debit': sum(vouchers.mapped('price_used')),
                        'credit': 0.0,
                        'analytic_distribution': {d.center_expense_id.id: 100} if d.center_expense_id else {}
                    }),
                ]
            }
            AccountMove.sudo().create(move_vals)._post()
        else:
            _logger.info(f'Phương thức thanh toán không có hoặc chưa được cấu hình tài khoản!')
        return True

    def show_journal_items(self):
        self.ensure_one()
        all_related_moves = self._get_related_account_moves()
        jn_entry_voucher_gift = self.env['account.move'].sudo().search([('ss_id','=',self.id)])
        if jn_entry_voucher_gift:
            all_related_moves |= jn_entry_voucher_gift
        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'view_id':self.env.ref('account.view_move_line_tree').id,
            'domain': [('id', 'in', all_related_moves.mapped('line_ids').ids)],
            'context': {
                'journal_type':'general',
                'search_default_group_by_move': 1,
                'group_by':'move_id', 'search_default_posted':1,
            },
        }

class Acc(models.Model):
    _inherit = 'account.move'

    ss_id = fields.Many2one('pos.session')