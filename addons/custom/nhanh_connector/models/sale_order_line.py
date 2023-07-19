# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLineNhanh(models.Model):
    _inherit = 'sale.order.line'

    discount_price_unit = fields.Float('Đơn giá giảm', compute="_compute_discount_price_unit")
    odoo_price_unit = fields.Float('Đơn giá (Odoo)', compute="_compute_odoo_price_unit")
    discount_after_unit = fields.Float('Giá trị sau giảm', compute="_compute_discount_after_unit")


    def _compute_discount_after_unit(self):
        for line in self:
            line.discount_after_unit = line.price_unit - line.x_cart_discount_fixed_price

    def _compute_discount_price_unit(self):
        for item in self:
            if not item.product_uom_qty:
                item.discount_price_unit = 0
            else:
                item.discount_price_unit = item.x_cart_discount_fixed_price > 0 and item.x_cart_discount_fixed_price / item.product_uom_qty or 0

    def _compute_odoo_price_unit(self):
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            # if line.qty_invoiced > 0:
            #     continue
            if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
                line.odoo_price_unit = 0.0
            else:
                price = line.with_company(line.company_id)._get_display_price()
                line.odoo_price_unit = line.product_id._get_tax_included_unit_price(
                    line.company_id,
                    line.order_id.currency_id,
                    line.order_id.date_order,
                    'sale',
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id
                )
