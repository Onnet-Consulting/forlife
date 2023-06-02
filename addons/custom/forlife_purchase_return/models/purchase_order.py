import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_return = fields.Boolean(string="Is return?", default=False)
    return_purchase_ids = fields.One2many('purchase.order', 'origin_purchase_id', string="Return Purchases", copy=False)
    origin_purchase_id = fields.Many2one('purchase.order', string="Origin Purchase", copy=False)
    count_return_purchase = fields.Integer(compute="_compute_count_return_purchase", store=True, copy=False)

    warehouse_material = fields.Many2one('stock.location', string="Lý do nhập NPL")

    @api.onchange('partner_id')
    def _onchange_partner_id_return(self):
        if self.partner_id and self.is_return:
            # self.location_id = self.partner_id.property_stock_supplier.id
            self.dest_address_id = self.partner_id.id

    @api.model
    def _get_picking_type(self, company_id):
        res = super(PurchaseOrder, self)._get_picking_type(company_id)
        if self._context.get('default_is_return', False):
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)])
            if not picking_type:
                picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
            res = picking_type[:1]
        return res

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

    def action_approved(self):
        for po in self:
            if po.is_return and not po.warehouse_material and po.order_line_production_order:
                raise UserError("Chi tiết đơn hàng trả có sản phẩm đính kèm cần xác định kho nhập NPL. Vui lòng liên hệ thủ kho để xác nhận vị trí nhập kho NPL.")
        super(PurchaseOrder, self).action_approved()

    def _prepare_picking(self):
        vals = super(PurchaseOrder, self)._prepare_picking()
        if self.is_return:
            if type(vals) == list:
                for val in vals:
                    val.update({
                        'location_id': self.location_id.id,
                        'location_dest_id': self.partner_id.property_stock_supplier.id,
                        # 'picking_type_id': self.picking_type_id.return_picking_type_id.id
                        'origin': val.get('origin', '') + _(' Return')
                    })
            else:
                vals.update({
                    'location_id': self.location_id.id,
                    'location_dest_id': self.partner_id.property_stock_supplier.id,
                    # 'picking_type_id': self.picking_type_id.return_picking_type_id.id
                    'origin': vals.get('origin', '') + _(' Return')
                })
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

    def _create_picking(self):
        res = super(PurchaseOrder, self)._create_picking()
        for po in self:
            if po.picking_ids and po.is_return:
                for picking in po.picking_ids:
                    picking.write({'location_id': po.location_id.id, 'location_dest_id': po.partner_id.property_stock_supplier.id})
        return res


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

                # return_line = self.env['purchase.order.line'].search([('origin_po_line_id', '=', line.id)])
                # total += sum(return_line.mapped('qty_returned'))
                line.qty_returned = total

    def _prepare_account_move_line(self):
        vals = super(PurchaseOrderLine, self)._prepare_account_move_line()
        if self.order_id.is_return:
            vals.update({'return_price_unit': -self.price_unit})
        if self.qty_returned:
            vals.update({'qty_returned': self.qty_returned})
        return vals


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals_list):
        if 'invoice_line_ids' in vals_list:
            for line in vals_list['invoice_line_ids']:
                if line[0] == 0:
                    if line[2].get('return_price_unit'):
                        line[2]['price_unit'] = line[2].pop('return_price_unit')
                    if line[2].get('qty_returned'):
                        line[2]['quantity'] = line[2].get('quantity') - line[2].pop('qty_returned')

        return super(AccountMove, self).create(vals_list)
