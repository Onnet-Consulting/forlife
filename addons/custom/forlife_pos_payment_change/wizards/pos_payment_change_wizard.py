from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosPaymentChangeWizard(models.TransientModel):
    _name = "pos.payment.change.wizard"
    _description = 'PoS Payment Change Wizard'

    order_id = fields.Many2one(comodel_name='pos.order', string='Order', readonly=True)
    line_ids = fields.One2many('pos.payment.change.wizard.line', 'wizard_id', 'Payment Lines', readonly=False)
    amount_total = fields.Float(string='Total', readonly=True)

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
        print('=============-=-=-=-=-============')
        order.change_payment(order.id, new_payments)

        # Note. Because of the poor design of the closing session process
        # in Odoo, we call _check_pos_session_balance() that sets
        # balance_end_real with balance_end for 'non cash' journals
        if order.session_id.state == 'closing_control':
            order.session_id._check_pos_session_balance()

        return True
        # return {'type': 'ir.actions.act_window_close'}
