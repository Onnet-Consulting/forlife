# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    price_unit_excl = fields.Monetary(compute="price_unit_incl_excl")
    price_unit_incl = fields.Monetary(compute="price_unit_incl_excl")

    def get_pk_tax(self):
        tax_ids = []
        if self.tax_ids_after_fiscal_position:
            for tax_id in self.tax_ids_after_fiscal_position:
                tax_ids.append(str(tax_id.id))
        return "_".join(tax_ids)

    def get_pk_synthetic(self):
        pk = f"{self.product_id.barcode}_{float(abs(self.price_unit_excl))}_{self.get_pk_tax()}"
        return pk

    def get_pk_synthetic_line_discount(self):
        pk = f"{self.product_id.barcode}_{self.get_pk_tax()}"
        return pk

    @api.depends('price_subtotal', 'price_subtotal_incl')
    def price_unit_incl_excl(self):
        for r in self:
            price_unit_excl = 0
            price_unit_incl = 0
            if not r.is_promotion:
                discount_details_lines = self.env['pos.order.line'].search([
                    ('is_promotion', '=', True),
                    ('order_id', '=', r.order_id.id),
                    ('product_src_id', '=', r.product_id.id),
                    ('promotion_type', 'in', ['ctkm', 'make_price', 'product_defective', 'handle'])
                ])
                sum_km_excl =sum(discount_details_lines.mapped('price_subtotal'))
                sum_km_incl =sum(discount_details_lines.mapped('price_subtotal'))
                # sum_km = sum(r.discount_details_lines.filtered(lambda x: x.type in ('ctkm', ' make_price', 'product_defactive', 'handle')).mapped('money_reduced'))
                # tax = sum(r.tax_ids_after_fiscal_position.mapped('amount')) / 100
                price_unit_excl = (r.price_subtotal + sum_km_excl)/r.qty
                price_unit_incl = (r.price_subtotal_incl + sum_km_incl)/r.qty
            r.price_unit_excl = price_unit_excl
            r.price_unit_incl = price_unit_incl
