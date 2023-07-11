from odoo import api, fields, models, Command

class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _convert_to_tax_base_line_dict(
            self, base_line,
            partner=None, currency=None, product=None, taxes=None, price_unit=None, quantity=None,
            discount=None, account=None, analytic_distribution=None, price_subtotal=None,
            is_refund=False, rate=None,
            handle_price_include=None,
            extra_context=None,
    ):
        rslt = super(AccountTax, self)._convert_to_tax_base_line_dict(base_line, partner, currency, product, taxes, price_unit, quantity, discount, account, analytic_distribution, price_subtotal, is_refund, rate, handle_price_include, extra_context)
        if 'x_cart_discount_fixed_price' in self._context:
            rslt['x_cart_discount_fixed_price'] = self._context.get('x_cart_discount_fixed_price')
        return rslt

    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False, early_pay_discount_computation=None, early_pay_discount_percentage=None):
        to_update_vals, tax_values_list = super(AccountTax, self)._compute_taxes_for_single_line(base_line, handle_price_include, include_caba_tags, early_pay_discount_computation, early_pay_discount_percentage)

        if 'x_cart_discount_fixed_price' in base_line:
            to_update_vals['price_subtotal'] = to_update_vals['price_subtotal'] - base_line['x_cart_discount_fixed_price']
            to_update_vals['price_total'] = to_update_vals['price_total'] - base_line['x_cart_discount_fixed_price']
        return to_update_vals, tax_values_list
