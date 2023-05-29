import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_return = fields.Boolean(string="Is return?", default=False)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_returned = fields.Float(string="Returned Qty", digits='Product Unit of Measure', compute="_compute_qty_returned", store=True)

    # FIXME: to using tracking msg
    # def _track_qty_returned(self, new_qty):
    #     self.ensure_one()
    #     if new_qty != self.qty_returned and self.order_id.state == 'purchase':
    #         self.order_id.message_post_with_view(
    #             'purchase.track_po_line_qty_returned_template',
    #             values={'line': self, 'qty_returned': new_qty},
    #             subtype_id=self.env.ref('mail.mt_note').id
    #         )

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_returned(self):
        for line in self:
            if line.qty_received_method == 'stock_moves':
                total = 0.0
                for move in line._get_po_line_moves():
                    if move.state == 'done':
                        if move._is_purchase_return():
                            if move.to_refund:
                                total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')

                # line._track_qty_returned(total)
                line.qty_returned = total
