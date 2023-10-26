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

    # @api.model
    # def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False, early_pay_discount_computation=None, early_pay_discount_percentage=None):
    #     to_update_vals, tax_values_list = super(AccountTax, self)._compute_taxes_for_single_line(base_line, handle_price_include, include_caba_tags, early_pay_discount_computation, early_pay_discount_percentage)
    #
    #     if 'x_cart_discount_fixed_price' in base_line:
    #         to_update_vals['price_subtotal'] = to_update_vals['price_subtotal'] - base_line['x_cart_discount_fixed_price']
    #         to_update_vals['price_total'] = to_update_vals['price_total'] - base_line['x_cart_discount_fixed_price']
    #     return to_update_vals, tax_values_list

    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False, early_pay_discount_computation=None, early_pay_discount_percentage=None):
        orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        if base_line.get('x_cart_discount_fixed_price') and base_line.get('quantity'):
            discount_price_unit = base_line.get('x_cart_discount_fixed_price') > 0 and base_line.get('x_cart_discount_fixed_price') / base_line.get('quantity') or 0
            if discount_price_unit:
                orig_price_unit_after_discount -= discount_price_unit

        price_unit_after_discount = orig_price_unit_after_discount
        taxes = base_line['taxes']._origin
        currency = base_line['currency'] or self.env.company.currency_id
        rate = base_line['rate']
        if early_pay_discount_computation in ('included', 'excluded'):
            remaining_part_to_consider = (100 - early_pay_discount_percentage) / 100.0
            price_unit_after_discount = remaining_part_to_consider * price_unit_after_discount

        if taxes:

            if handle_price_include is None:
                manage_price_include = bool(base_line['handle_price_include'])
            else:
                manage_price_include = handle_price_include

            taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                price_unit_after_discount,
                currency=currency,
                quantity=base_line['quantity'],
                product=base_line['product'],
                partner=base_line['partner'],
                is_refund=base_line['is_refund'],
                handle_price_include=manage_price_include,
                include_caba_tags=include_caba_tags,
            )

            to_update_vals = {
                'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
                'price_subtotal': taxes_res['total_excluded'],
                'price_total': taxes_res['total_included'],
            }

            if early_pay_discount_computation == 'excluded':
                new_taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                    orig_price_unit_after_discount,
                    currency=currency,
                    quantity=base_line['quantity'],
                    product=base_line['product'],
                    partner=base_line['partner'],
                    is_refund=base_line['is_refund'],
                    handle_price_include=manage_price_include,
                    include_caba_tags=include_caba_tags,
                )
                for tax_res, new_taxes_res in zip(taxes_res['taxes'], new_taxes_res['taxes']):
                    delta_tax = new_taxes_res['amount'] - tax_res['amount']
                    tax_res['amount'] += delta_tax
                    to_update_vals['price_total'] += delta_tax

            tax_values_list = []
            for tax_res in taxes_res['taxes']:
                tax_amount = tax_res['amount'] / rate
                if self.company_id.tax_calculation_rounding_method == 'round_per_line':
                    tax_amount = currency.round(tax_amount)
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id'])
                tax_values_list.append({
                    **tax_res,
                    'tax_repartition_line': tax_rep,
                    'base_amount_currency': tax_res['base'],
                    'base_amount': currency.round(tax_res['base'] / rate),
                    'tax_amount_currency': tax_res['amount'],
                    'tax_amount': tax_amount,
                })
        else:
            price_subtotal = currency.round(price_unit_after_discount * base_line['quantity'])
            to_update_vals = {
                'tax_tag_ids': [Command.clear()],
                'price_subtotal': price_subtotal,
                'price_total': price_subtotal,
            }
            tax_values_list = []

        return to_update_vals, tax_values_list