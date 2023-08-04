# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from datetime import date, datetime


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        res = super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)
        # copy promotion từ đơn hàng qua hóa đơn
        if res and sale_orders.promotion_ids:
            res.write({
                'promotion_ids': [(0, 0, {
                    "product_id": prm.product_id.id,
                    "partner_id": sale_orders[0].delivery_carrier_id.partner_id.id if sale_orders.delivery_carrier_id.partner_id and prm.promotion_type == 'customer_shipping_fee' else False,
                    "value": prm.value,
                    "promotion_type": prm.promotion_type,
                    "account_id": prm.account_id.id,
                    "analytic_account_id": prm.analytic_account_id.id,
                    "description": prm.description,
                    "move_id": res.id,
                    "tax_id": prm.tax_id,
                }) for prm in sale_orders.promotion_ids]
            })

        return res

