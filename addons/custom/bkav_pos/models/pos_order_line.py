# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    price_bkav = fields.Monetary(compute="_compute_price_bkav")
    is_general = fields.Boolean(string="Đã chạy tổng hợp cuối ngày", related="order_id.is_general")


    @api.depends('price_subtotal_incl')
    def _compute_price_bkav(self):
        for r in self:
            sum_km = sum(r.discount_details_lines.filtered(lambda x: x.type in ('ctkm', ' make_price', 'product_defactive', 'handle')).mapped('money_reduced'))
            tax = sum(r.tax_ids_after_fiscal_position.mapped('amount')) / 100
            r.price_bkav = (r.price_subtotal_incl - sum_km) / (r.qty*(1 + tax))
