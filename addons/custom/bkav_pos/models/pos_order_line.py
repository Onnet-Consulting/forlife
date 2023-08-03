# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    price_bkav = fields.Monetary(compute="_compute_price_bkav")
    price_unit_excl = fields.Monetary(compute="price_unit_incl_excl")
    # price_unit_incl = fields.Monetary(compute="price_unit_incl_excl")

    @api.depends('price_subtotal_incl')
    def _compute_price_bkav(self):
        for r in self:
            sum_km = sum(r.discount_details_lines.filtered(lambda x: x.type in ('ctkm', ' make_price', 'product_defactive', 'handle')).mapped('money_reduced'))
            tax = sum(r.tax_ids_after_fiscal_position.mapped('amount')) / 100
            r.price_bkav = (r.price_subtotal_incl - sum_km) / (r.qty*(1 + tax))


    @api.depends('price_subtotal')
    def price_unit_incl_excl(self):
        for r in self:
            price_unit_excl = 0
            # price_unit_incl = 0
            if not r.is_promotion:
                line_km = self.env['pos.order.line'].search([
                    ('is_promotion', '=', True),
                    ('product_src_id', '=', r.product_id.id),
                    ('promotion_type', 'in', ['ctkm', 'make_price', 'product_defective', 'handle'])
                ]).mapped('price_subtotal')
                sum_km =sum(line_km)

                # sum_km = sum(r.discount_details_lines.filtered(lambda x: x.type in ('ctkm', ' make_price', 'product_defactive', 'handle')).mapped('money_reduced'))
                # tax = sum(r.tax_ids_after_fiscal_position.mapped('amount')) / 100
                price_unit_excl = (r.price_subtotal + sum_km)/r.qty
                # price_unit_incl = (r.price_subtotal_incl - sum_km)/r.qty
            r.price_unit_excl = price_unit_excl
            # r.price_unit_incl = price_unit_incl
