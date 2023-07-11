from odoo import api, fields, models

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
        print(self._context)
        return super(AccountTax, self)._convert_to_tax_base_line_dict(base_line, partner, currency, product, taxes, price_unit, quantity, discount, account, analytic_distribution, price_subtotal, is_refund, rate, handle_price_include, extra_context)