# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from contextlib import contextmanager

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # @api.onchange('amount_currency', 'currency_id')
    # def _inverse_amount_currency(self):
    #     if self.move_id.origin_invoice_id:
    #         for line in self:
    #             line.amount_currency = line.balance
    #     else:
    #         return super()._inverse_amount_currency()
    #
    # def _convert_to_tax_line_dict(self):
    #     """ Convert the current record to a dictionary in order to use the generic taxes computation method
    #     defined on account.tax.
    #     :return: A python dictionary.
    #     """
    #     self.ensure_one()
    #     if self.filtered(lambda r: r.move_id.origin_invoice_id):
    #         sign = 1 if (self.move_id.invoice_type == 'increase' and self.move_id.move_type == 'in_invoice') or (self.move_id.invoice_type == 'decrease' and self.move_id.move_type == 'in_refund') else -1
    #         return self.env['account.tax']._convert_to_tax_line_dict(
    #             self,
    #             partner=self.partner_id,
    #             currency=self.currency_id,
    #             taxes=self.tax_ids,
    #             tax_tags=self.tax_tag_ids,
    #             tax_repartition_line=self.tax_repartition_line_id,
    #             group_tax=self.group_tax_id,
    #             account=self.account_id,
    #             analytic_distribution=self.analytic_distribution,
    #             tax_amount=sign * self.amount_currency,
    #         )
    #     else:
    #         return super()._convert_to_tax_line_dict()
    #
    # @api.depends('balance', 'move_id.is_storno')
    # def _compute_debit_credit(self):
    #     if self.move_id:
    #         if self.move_id[0].invoice_type == 'decrease' and self.move_id[0].origin_invoice_id and not self.env.context.get('noonchange'):
    #             balance_payment_term = 0
    #             self.env.context = self.with_context(noonchange=True).env.context
    #             for line in self.sorted(lambda x: x.display_type, reverse=True):
    #                 if line.display_type == 'product':
    #                     balance_payment_term += abs(line.balance)
    #                     line.update({
    #                         'debit': 0,
    #                         'credit': abs(line.balance),
    #                         'balance': -abs(line.balance)
    #                     })
    #                 elif line.display_type == 'tax':
    #                     balance_payment_term += sum(line.move_id.line_ids.filtered(lambda x: x.product_id).mapped('tax_amount'))
    #                     line.update({
    #                         'debit': 0,
    #                         'credit': sum(line.move_id.line_ids.filtered(lambda x: x.product_id).mapped('tax_amount')),
    #                         'balance': -sum(line.move_id.line_ids.filtered(lambda x: x.product_id).mapped('tax_amount'))
    #                     })
    #                 else:
    #                     line.update({
    #                         'debit': int(balance_payment_term),
    #                         'credit': 0,
    #                         'balance': balance_payment_term
    #                     })
    #             if self.ids:
    #                 self._cr.commit()
    #         else:
    #             if self.move_id[0].invoice_type != 'decrease' and not self.env.context.get('noonchange'):
    #                 return super(AccountMoveLine, self)._compute_debit_credit()
    #     else:
    #         return super(AccountMoveLine, self)._compute_debit_credit()
