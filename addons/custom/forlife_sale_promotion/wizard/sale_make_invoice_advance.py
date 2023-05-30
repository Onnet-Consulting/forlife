# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_is_zero


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        res = super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)
        if res and sale_orders.promotion_ids:
            res.write({
                'promotion_ids': [(0, 0, {
                    "product_id": prm.product_id.id,
                    "value": prm.value,
                    "account_id": prm.account_id.id,
                    "analytic_account_id": prm.analytic_account_id.id,
                    "description": prm.description,
                    "move_id": res.id
                }) for prm in sale_orders.promotion_ids]
            })

        return res

