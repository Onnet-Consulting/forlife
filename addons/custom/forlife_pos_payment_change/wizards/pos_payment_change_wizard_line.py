from odoo import fields, models, api


class PosPaymentChangeWizardOldLine(models.TransientModel):
    _name = "pos.payment.change.wizard.line"
    _description = "PoS Payment Change Wizard Line"

    @api.model
    def domain_new_payment_method_id(self):
        PosOrder = self.env['pos.order']
        order = PosOrder.browse(self.env.context.get('active_id'))
        return [('id', 'in', order.mapped('session_id.payment_method_ids').ids),
                ('is_voucher', '=', False)]

    wizard_id = fields.Many2one("pos.payment.change.wizard", required=True)
    payment_id = fields.Many2one("pos.payment", required=True, readonly=True, string="Payment")
    old_payment_method_id = fields.Many2one(
        "pos.payment.method", string="Payment Method", required=True, readonly=True)
    is_voucher = fields.Boolean(related='old_payment_method_id.is_voucher')
    currency_id = fields.Many2one(
        "res.currency", store=True, string="Currency", readonly=True, help="Utility field to express amount currency")
    amount = fields.Monetary(
        related='payment_id.amount', required=True, readonly=True, currency_field="currency_id")
    new_payment_method_id = fields.Many2one(
        'pos.payment.method', 'Payment Method', required=False, readonly=False, domain=lambda s: s.domain_new_payment_method_id())
