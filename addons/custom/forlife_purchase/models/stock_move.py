# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_pk_purchase = fields.Boolean(string="Là phiếu của Po", default=False)
    order_line_count = fields.Integer('Order Line Count', compute='_compute_order_line_count')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")

    def write(self, vals):
        print(self.state)
        old_line_count = len(self.move_line_ids_without_package)
        new_line_count = len(vals.get('move_line_ids_without_package', []))
        if (new_line_count > old_line_count) and self.state:
            raise ValidationError('Cannot add additional order lines.')
        return super(StockPicking, self).write(vals)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    purchase_uom = fields.Many2one('uom.uom', string="Đơn vị mua")
    quantity_change = fields.Float(string="Số lượng quy đổi")
    quantity_purchase_done = fields.Float(string="Số lượng mua hoàn thành")

    @api.onchange('quantity_change', 'quantity_purchase_done')
    def onchange_quantity_purchase_done(self):
        self.qty_done = self.quantity_purchase_done * self.quantity_change


class StockMove(models.Model):
    _inherit = 'stock.move'