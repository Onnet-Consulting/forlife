# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    show_vnpay_config = fields.Boolean(compute='_compute_show_vnpay_config')
    vnpay_url = fields.Char(string='VNPay Endpoint')
    vnpay_secret_code = fields.Char(string='VNPay Secret Code')
    vnpay_ipn_secret_code = fields.Char(string="VNPay IPN Secret Code")
    vnpay_merchant_code = fields.Char(string='VNPay Merchant Code', help='merchantCode')
    vnpay_terminal_code = fields.Char(string='VNPay Terminal Code', help='terminalCode')
    vnpay_merchant_method_code_card = fields.Char(string='VNPay Merchant Method Code (Card)',
                                                  help='merchantMethodCode for Card')
    vnpay_success_url = fields.Char(string='VNPay Success URL',
                                    help='Redirect request to this URL after payment successful')
    vnpay_cancel_url = fields.Char(string='VNPay Cancel URL', help='Redirect request to this URL after payment failed')

    @api.depends('payment_method_ids')
    def _compute_show_vnpay_config(self):
        for config in self:
            config.show_vnpay_config = bool(config.payment_method_ids.filtered(lambda payment:
                                                                               not payment.hide_use_payment_terminal
                                                                               and payment.use_payment_terminal == 'vnpay'))

    def _get_vnpay_channel_name(self):
        self.ensure_one()
        return '["{}","{}"]'.format("vnpay_payment_response", self.id)

    def _notify_vnpay_payment_response(self, message):
        self.ensure_one()
        notifications = [
            [self._get_vnpay_channel_name(), 'pos.config/vnpay_payment_response', message]
        ]
        self.env['bus.bus']._sendmany(notifications)
        return True
