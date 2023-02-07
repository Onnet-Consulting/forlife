import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosPaymentChangeWizard(models.TransientModel):
    _name = "pos.payment.change.wizard"
    _description = 'PoS Payment Change Wizard'

    order_id = fields.Many2one(comodel_name='pos.order', string='Order', readonly=True)
    line_ids = fields.One2many('pos.payment.change.wizard.line', 'wizard_id', 'Payment Lines', readonly=False)
    amount_total = fields.Float(string='Total', readonly=True)
    move_ids = fields.Many2many('account.move', related='order_id.change_payment_move_ids', readonly=False)
    payment_move_count = fields.Integer(related='order_id.payment_move_count')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        PosOrder = self.env['pos.order']
        order = PosOrder.browse(self._context.get('active_id'))
        old_lines_vals = []
        for payment in order.payment_ids:
            old_lines_vals.append((0, 0, {
                'old_payment_method_id': payment.payment_method_id.id,
                'payment_id': payment.id,
                'amount': payment.amount,
                'currency_id': payment.currency_id.id
            }))
        res.update({
            'order_id': order.id,
            'amount_total': order.amount_total,
            'line_ids': old_lines_vals})
        return res

    def button_change_payment(self):
        self.ensure_one()
        order = self.order_id
        new_payments = [{
            'payment_id': line.payment_id.id,
            'payment_method_id': line.new_payment_method_id.id,
            'amount': line.amount,
            }
            for line in self.line_ids]
        order.change_payment(order.id, new_payments)

        # Note. Because of the poor design of the closing session process
        # in Odoo, we call _check_pos_session_balance() that sets
        # balance_end_real with balance_end for 'non cash' journals
        if order.session_id.state == 'closing_control':
            order.session_id._check_pos_session_balance()

        return True

    def _prepare_default_reversal(self, move):
        reverse_date = datetime.date.today()
        default_journal_id = self.order_id._get_default_payment_change_journal()
        return {
            'ref': _('Reversal of: %s', move.name),
            'date': reverse_date,
            'invoice_date_due': reverse_date,
            'invoice_date': move.is_invoice(include_receipts=True) and reverse_date or False,
            'journal_id': default_journal_id.id,
            'invoice_payment_term_id': None,
            'invoice_user_id': move.invoice_user_id.id,
            'auto_post': 'at_date' if reverse_date > fields.Date.context_today(self) else 'no',
        }

    def button_reverse_entry(self):
        reversed_moves = self.move_ids.filtered(lambda m: m.state == 'posted').mapped('reversed_entry_id')
        to_do_moves = self.move_ids.filtered(lambda m: m.state == 'posted' and not m.reversed_entry_id) - reversed_moves
        if not to_do_moves:
            raise UserError(_('There are no journal entry to reverse or cancel!'))
        # Create default values.
        default_values_list = []
        for move in to_do_moves:
            default_values_list.append(self._prepare_default_reversal(move))

        reverse_moves = to_do_moves._reverse_moves(default_values_list, cancel=True)
        self.order_id.change_payment_move_ids |= reverse_moves
        return True
