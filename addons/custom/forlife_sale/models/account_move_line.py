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

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        rslt = super(AccountMoveLine, self)._compute_totals()
        for line in self:
            x_cart_discount_fixed_price = 0
            check = bool(line.x_cart_discount_fixed_price == line.price_unit * line.discount * line.quantity / 100)
            if check:
                x_cart_discount_fixed_price = 0
            if line.discount == 0:
                x_cart_discount_fixed_price = line.x_cart_discount_fixed_price
            line.price_subtotal = line.price_subtotal - x_cart_discount_fixed_price
            line.price_total = line.price_subtotal - x_cart_discount_fixed_price
        return rslt