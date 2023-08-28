# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from datetime import date, datetime


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):

        # copy promotion từ đơn hàng qua hóa đơn
        promotion_vals = []
        if sale_orders.promotion_ids:
            for prm in sale_orders.promotion_ids:
                if prm.promotion_type in ['customer_shipping_fee', 'nhanh_shipping_fee']:
                    val = (0, 0, {
                        "product_id": prm.product_id.id,
                        "value": prm.value,
                        "product_uom_qty": prm.product_uom_qty,
                        "promotion_type": prm.promotion_type,
                        "account_id": prm.account_id.id,
                        "analytic_account_id": prm.analytic_account_id.id,
                        "description": prm.description,
                        "tax_id": prm.tax_id,
                    })
                    promotion_vals.append(val)

                if prm.order_line_id.qty_to_invoice and prm.promotion_type not in ['customer_shipping_fee', 'nhanh_shipping_fee']:
                    value = round(prm.value * (prm.order_line_id.qty_to_invoice / prm.order_line_id.product_uom_qty), 0)
                    val = (0, 0, {
                        "product_id": prm.product_id.id,
                        "partner_id": sale_orders[0].delivery_carrier_id.partner_id.id if sale_orders.delivery_carrier_id.partner_id and prm.promotion_type == 'customer_shipping_fee' else False,
                        "value": value,
                        "product_uom_qty": prm.product_uom_qty,
                        "promotion_type": prm.promotion_type,
                        "account_id": prm.account_id.id,
                        "analytic_account_id": prm.analytic_account_id.id,
                        "description": prm.description,
                        "tax_id": prm.tax_id,
                    })
                    promotion_vals.append(val)
                if prm.promotion_type in ['out_point', 'in_point']:
                    val = (0, 0, {
                        "product_id": prm.product_id.id,
                        "partner_id": sale_orders[0].delivery_carrier_id.partner_id.id if sale_orders.delivery_carrier_id.partner_id and prm.promotion_type == 'customer_shipping_fee' else False,
                        "value": prm.value,
                        "product_uom_qty": prm.product_uom_qty,
                        "promotion_type": prm.promotion_type,
                        "account_id": prm.account_id.id,
                        "analytic_account_id": prm.analytic_account_id.id,
                        "description": prm.description,
                        "tax_id": prm.tax_id,
                    })
                    promotion_vals.append(val)

        res = super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)

        if len(sale_orders.mapped('x_sale_type')) == 1:
            res.write({
                'purchase_type': sale_orders.mapped('x_sale_type')[0],
            })

        if promotion_vals:
            res.write({
                'promotion_ids': promotion_vals
            })

        return res

