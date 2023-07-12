from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    code = fields.Char(string='Code')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code, company_id)', 'Code must be unique per company!')
    ]

    @api.model
    def _compute_taxes_for_single_line(
        self, 
        base_line, 
        handle_price_include=True, 
        include_caba_tags=False, 
        early_pay_discount_computation=None, 
        early_pay_discount_percentage=None
    ):
        try:
            if float(base_line["record"].x_cart_discount_fixed_price) > 0:
                base_line['discount'] = (base_line["record"].x_cart_discount_fixed_price/base_line['price_unit']) * 100
        except Exception as e:
            pass
        

        to_update_vals, tax_values_list = super()._compute_taxes_for_single_line(
            base_line,
            handle_price_include=handle_price_include,
            include_caba_tags=include_caba_tags,
            early_pay_discount_computation=early_pay_discount_computation,
            early_pay_discount_percentage=early_pay_discount_percentage
        )
        return to_update_vals, tax_values_list