# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state', 'invoice_lines.move_id.select_type_inv')
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self:
            for inv_line in line._get_invoice_lines():
                if inv_line.move_id.select_type_inv in ('expense', 'labor'):
                    line.qty_invoiced -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                    line.qty_to_invoice += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)