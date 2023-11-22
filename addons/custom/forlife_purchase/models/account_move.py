# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta, datetime
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_from_ncc = fields.Boolean('From Ncc')
    reference = fields.Char(string='Tài liệu')
    is_trade_discount_move = fields.Boolean('Is trade discount move', default=False)
    is_check = fields.Boolean()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if self.purchase_order_product_id and 'origin_invoice_id' not in default and not self._context.get('move_reverse_cancel'):
            default.update({
                'invoice_line_ids': [],
                'line_ids': [],
                'purchase_order_product_id': False,
                'receiving_warehouse_id': False,
            })
        return super().copy(default)

    def action_post(self):
        for rec in self:
            if rec.purchase_order_product_id:
                min_date_approve = (min(rec.purchase_order_product_id.mapped('date_approve')) + timedelta(hours=7)).date()
                if min_date_approve > rec.date:
                    message = 'Ngày kế toán (%s) nhỏ hơn ngày Xác nhận đơn mua hàng (%s). Vui lòng kiểm tra lại!' % (datetime.strftime(rec.date, '%d/%m/%Y'), datetime.strftime(min_date_approve, '%d/%m/%Y'))
                    raise UserError(message)
            for invoice_line_id in rec.invoice_line_ids.filtered(lambda x: x.stock_move_id):
                qty_invoiced = invoice_line_id.stock_move_id.qty_invoiced + invoice_line_id.stock_move_id.qty_to_invoice
                invoice_line_id.stock_move_id.write({
                    'qty_invoiced': qty_invoiced,
                    'qty_to_invoice': 0,
                    'qty_refunded': 0,
                })
        res = super(AccountMove, self).action_post()
        return res

    def button_cancel(self):
        for rec in self:
            for invoice_line_id in rec.invoice_line_ids.filtered(lambda x: x.stock_move_id):
                qty_invoiced = invoice_line_id.stock_move_id.qty_invoiced - invoice_line_id.quantity
                if qty_invoiced <= 0:
                    qty_invoiced = 0
                invoice_line_id.stock_move_id.write({
                    'qty_invoiced': qty_invoiced,
                    'qty_to_invoice': 0,
                    'qty_refunded': 0,
                })
        return super(AccountMove, self).button_cancel()

    def unlink(self):
        for rec in self:
            for invoice_line_id in rec.invoice_line_ids.filtered(lambda x: x.stock_move_id):
                qty_invoiced = invoice_line_id.stock_move_id.qty_invoiced - invoice_line_id.quantity
                if qty_invoiced <= 0:
                    qty_invoiced = 0
                invoice_line_id.stock_move_id.write({
                    'qty_invoiced': qty_invoiced,
                    'qty_to_invoice': 0,
                    'qty_refunded': 0,
                })
        return super(AccountMove, self).unlink()

    def button_draft(self):
        for rec in self:
            for invoice_line_id in rec.invoice_line_ids.filtered(lambda x: x.stock_move_id):
                invoice_line_id.stock_move_id.write({
                    'qty_to_invoice': invoice_line_id.quantity
                })
        return super(AccountMove, self).button_draft()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        res = super().copy(default)
        if self.env.context.get('move_reverse_cancel'):
            if res.reversed_entry_id and res.reversed_entry_id.vendor_back_ids and res.line_ids:
                for vendor_back_id in res.reversed_entry_id.vendor_back_ids:
                    vendor_back_id.copy({'vendor_back_id': res.id})
                for account_expense_labor_detail_id in res.reversed_entry_id.account_expense_labor_detail_ids:
                    account_expense_labor_detail_id.copy({'move_id': res.id})
                if res.reversed_entry_id.vendor_back_ids.filtered(lambda x: x.tax_back > 0):
                    origin_tax_line_ids = res.reversed_entry_id.line_ids.filtered(lambda x: x.display_type == 'tax')
                    if origin_tax_line_ids:
                        for origin_tax_line_id in origin_tax_line_ids:
                            tax_line_id = origin_tax_line_id.copy({'move_id': res.id})
                            debit = tax_line_id.debit
                            credit = tax_line_id.credit
                            tax_line_id.write({
                                'debit': credit,
                                'credit': debit,
                            })
        return res
