# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Exchange')
    manual_currency_exchange_rate = fields.Float('Rate', digits=(12, 6))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)
    is_from_ncc = fields.Boolean('From Ncc')
    reference = fields.Char(string='Tài liệu')
    is_trade_discount_move = fields.Boolean('Is trade discount move', default=False)
    is_check = fields.Boolean()

    def action_post(self):
        for rec in self:
            if rec.purchase_order_product_id:
                for item in rec.purchase_order_product_id:
                    item.write({
                        'invoice_status_fake': 'invoiced',
                    })
            if rec.receiving_warehouse_id:
                rec.receiving_warehouse_id.write({
                    'ware_check': True
                })
        res = super(AccountMove, self).action_post()
        return res

    def button_cancel(self):
        for rec in self:
            if rec.receiving_warehouse_id:
                rec.receiving_warehouse_id.write({
                    'ware_check': False
                })
        return super(AccountMove, self).button_cancel()

    def unlink(self):
        for rec in self:
            if rec.receiving_warehouse_id:
                rec.receiving_warehouse_id.write({
                    'ware_check': False
                })
        return super(AccountMove, self).unlink()

    def button_draft(self):
        for rec in self:
            if rec.receiving_warehouse_id:
                rec.receiving_warehouse_id.write({
                    'ware_check': False
                })
        return super(AccountMove, self).button_draft()


