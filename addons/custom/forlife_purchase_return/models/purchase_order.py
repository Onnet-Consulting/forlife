import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_return = fields.Boolean(string="Is return?", default=False, copy=False)
    return_purchase_ids = fields.One2many('purchase.order', 'origin_purchase_id', string="Return Purchases", copy=False)
    origin_purchase_id = fields.Many2one('purchase.order', string="Origin Purchase", copy=False)
    count_return_purchase = fields.Integer(compute="_compute_count_return_purchase", store=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            # Ensures default picking type and currency are taken from the right company.
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New' and vals.get('is_return', False):
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
                vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order.return', sequence_date=seq_date) or '/'
        return super(PurchaseOrder, self).create(vals_list)

    @api.depends('return_purchase_ids', 'return_purchase_ids.custom_state')
    def _compute_count_return_purchase(self):
        for order in self:
            order.count_return_purchase = len(order.return_purchase_ids.filtered(lambda por: por.custom_state != 'cancel'))

    def _prepare_picking(self):
        vals = super(PurchaseOrder, self)._prepare_picking()
        if self.is_return:
            if type(vals) == list:
                for val in vals:
                    val.update({'location_id': self.source_location_id.id, 'origin': val.get('origin', '') + _(' Return')})
            else:
                vals.update({'location_id': self.source_location_id.id, 'origin': vals.get('origin', '') + _(' Return')})
        return vals

    def action_view_purchase_return(self):
        if self.return_purchase_ids:
            context = {'create': True, 'delete': True, 'edit': True}
            return {
                'name': _('Purchase Return'),
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', '=', self.return_purchase_ids.ids)],
                'context': context
            }


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    origin_po_line_id = fields.Many2one('purchase.order.line')
    qty_returned = fields.Integer(string="Returned Qty", compute="_compute_qty_returned", store=True)
    return_line_ids = fields.One2many('purchase.order.line', 'origin_po_line_id', string="Return Lines")

    # FIXME: to using tracking msg
    # def _track_qty_returned(self, new_qty):
    #     self.ensure_one()
    #     if new_qty != self.qty_returned and self.order_id.state == 'purchase':
    #         self.order_id.message_post_with_view(
    #             'purchase.track_po_line_qty_returned_template',
    #             values={'line': self, 'qty_returned': new_qty},
    #             subtype_id=self.env.ref('mail.mt_note').id
    #         )

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom',
        'return_line_ids.order_id', 'return_line_ids.order_id.custom_state', 'return_line_ids.move_ids.state')
    def _compute_qty_returned(self):
        for line in self:
            if line.order_id.is_return:
                total = 0.0
                for move in line._get_po_line_moves():
                    if move.state == 'done':
                        total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')

                line.qty_returned = total
            else:
                total = 0.0
                if line.qty_received_method == 'stock_moves':
                    for move in line._get_po_line_moves():
                        if move.state == 'done':
                            if move._is_purchase_return():
                                if move.to_refund:
                                    total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')

                return_line = self.env['purchase.order.line'].search([('origin_po_line_id', '=', line.id)])
                total += sum(return_line.mapped('qty_returned'))
                line.qty_returned = total
