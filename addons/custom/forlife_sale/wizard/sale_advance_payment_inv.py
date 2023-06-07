# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    # def _create_invoices(self, sale_orders):
    #     res = super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)
    #     if not self._context.get('active_id') or self.env['sale.order'].browse(
    #             self._context.get('active_id')).x_sale_type != 'service':
    #         return res
    #     for line in res.invoice_line_ids:
    #         if line.product_id:
    #             line.account_id = line.product_id.product_tmpl_id.property_account_income_id
    #     return res
