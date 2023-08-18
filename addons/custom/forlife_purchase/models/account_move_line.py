# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # fields lưu giá trị product chi phí cho hac toán phân bổ chi phí mua hàng
    product_expense_origin_id = fields.Many2one('product.product', string='Product Expense Origin')

    @api.onchange('product_uom_id')
    def _onchange_uom_id(self):
        ''' Recompute the 'price_unit' depending of the unit of measure. '''
        price_unit = self._get_computed_price_unit()

        # See '_onchange_product_id' for details.
        taxes = self._get_computed_taxes()
        if taxes and self.move_id.fiscal_position_id:
            price_subtotal = self._get_price_total_and_subtotal(price_unit=price_unit, taxes=taxes)['price_subtotal']
            accounting_vals = self._get_fields_onchange_subtotal(price_subtotal=price_subtotal,
                                                                 currency=self.move_id.company_currency_id)
            amount_currency = accounting_vals['amount_currency']
            price_unit = self._get_fields_onchange_balance(amount_currency=amount_currency, force_computation=True).get(
                'price_unit', price_unit)

        # Convert the unit price to the invoice's currency.
        company = self.move_id.company_id
        if self.move_id.apply_manual_currency_exchange:
            self.price_unit = price_unit * self.move_id.manual_currency_exchange_rate
        else:
            self.price_unit = company.currency_id._convert(price_unit, self.move_id.currency_id, company,
                                                           self.move_id.date, round=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            line.tax_ids = line._get_computed_taxes()
            line.product_uom_id = line._get_computed_uom()
            line.price_unit = line._get_computed_price_unit()

            # price_unit and taxes may need to be adapted following Fiscal Position
            line._set_price_and_tax_after_fpos()

            # Convert the unit price to the invoice's currency.
            company = line.move_id.company_id
            if line.move_id.apply_manual_currency_exchange:
                line.price_unit = line.price_unit * line.move_id.manual_currency_exchange_rate
            else:
                line.price_unit = company.currency_id._convert(line.price_unit, line.move_id.currency_id, company,
                                                               line.move_id.date, round=False)

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        for line in self:
            company = line.move_id.company_id
            if line.move_id.apply_manual_currency_exchange:
                balance = line.amount_currency / (1 / line.move_id.manual_currency_exchange_rate)
            else:
                balance = line.currency_id._convert(line.amount_currency, company.currency_id, company,
                                                    line.move_id.date)
            line.debit = balance if balance > 0.0 else 0.0
            line.credit = -balance if balance < 0.0 else 0.0
            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())