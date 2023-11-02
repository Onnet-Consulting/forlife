# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_cart_discount_fixed_price = fields.Float('Giảm giá cố định', digits=(16, 2))

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.
        :return: A python dictionary.
        """
        x_cart_discount_fixed_price = 0
        if self.x_cart_discount_fixed_price == self.price_unit * self.discount * self.quantity / 100:
            x_cart_discount_fixed_price = 0
        if self.discount == 0:
            x_cart_discount_fixed_price = self.x_cart_discount_fixed_price
        rslt = super(AccountMoveLine, self.with_context(x_cart_discount_fixed_price=x_cart_discount_fixed_price))._convert_to_tax_base_line_dict()
        return rslt

    # Hàm override từ Odoo base, tính lại giá tính thuế bằng cách trừ tiền giảm x_cart_discount_fixed_price
    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            # line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            line_discount_price_unit = line.price_unit
            # Compute price after discounting by fix amount
            if line.x_cart_discount_fixed_price and line.quantity:
                discount_price_unit = line.x_cart_discount_fixed_price > 0 and line.x_cart_discount_fixed_price / line.quantity or 0
                if discount_price_unit:
                    line_discount_price_unit -= discount_price_unit

            subtotal = line.quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal
