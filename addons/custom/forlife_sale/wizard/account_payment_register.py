# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        if self._context.get('active_id'):
            invoice_id = self.env['account.move'].browse(self._context.get('active_id'))
            move_id = self.env['account.move'].search([('ref', '=', invoice_id.name)])
            move_id.narration = invoice_id.narration
        return res
