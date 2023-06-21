# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_type_transfer = fields.Selection([('out','Out'),('in','In')], string='Type Transfer', default='out')


class AccountMove(models.Model):
    _inherit = 'account.move'

    def post(self):
        res = super(AccountMove, self).post()
        in_invoice_purchase_line_ids = False
        in_refund_purchase_line_ids = False
        for invoice in self.filtered(lambda x: x.type == 'in_invoice'):
            in_invoice_purchase_line_ids = invoice.mapped('invoice_line_ids.purchase_line_id')
        for invoice in self.filtered(lambda x: x.type == 'in_refund'):
            in_refund_purchase_line_ids = invoice.mapped('invoice_line_ids.purchase_line_id')
        if in_invoice_purchase_line_ids:
            for move_line_id in self.line_ids:
                move_line_id.x_type_transfer = 'in'
        if in_refund_purchase_line_ids:
            for move_line_id in self.line_ids:
                move_line_id.x_type_transfer = 'out'
        return res
