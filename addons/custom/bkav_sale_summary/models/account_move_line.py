from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    price_unit_excl = fields.Monetary(compute="price_unit_incl_excl")
    price_unit_incl = fields.Monetary(compute="price_unit_incl_excl")


    @api.depends('price_subtotal', 'price_unit', 'price_total')
    def price_unit_incl_excl(self):
        for r in self:
            price_unit_incl = r.price_unit * (1 - (r.discount / 100.0))
            if r.tax_ids:
                taxes_res = r.tax_ids.compute_all(
                    price_unit_incl,
                    is_refund=r.is_refund,
                )
                price_unit_excl = taxes_res['total_excluded']
            else:
                price_unit_excl = price_unit_incl

            r.price_unit_excl = price_unit_excl
            r.price_unit_incl = price_unit_incl