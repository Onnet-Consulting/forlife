from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    price_unit_excl = fields.Monetary(compute="price_unit_incl_excl")
    price_unit_incl = fields.Monetary(compute="price_unit_incl_excl")


    @api.depends('price_subtotal', 'price_unit')
    def price_unit_incl_excl(self):
        for r in self:
            price_unit_excl = 0
            price_unit_incl = 0
            if abs(r.quantity) > 0:
                price_unit_excl = r.price_subtotal/r.quantity
                price_unit_incl = r.price_unit
            r.price_unit_excl = price_unit_excl
            r.price_unit_incl = price_unit_incl