from odoo import fields, models, api, _
from collections import defaultdict
from odoo.exceptions import UserError


class PurchaseReturnWizardLine(models.TransientModel):
    _name = "purchase.return.wizard.line"
    _rec_name = 'product_id'
    _description = 'Purchase Return Wizard Line'

    wizard_id = fields.Many2one('purchase.return.wizard', string="Wizard")
    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('id', '=', product_id)]")
    purchase_received = fields.Integer("Received Quantity", required=True)
    purchase_returned = fields.Integer("Returned Quantity", required=True)
    purchase_remain = fields.Integer("Remain Quantity", required=True)
    exchange_quantity = fields.Float("Exchange", digits='Product Unit of Measure', required=True)
    quantity = fields.Integer("Quantity", digits='Product Unit of Measure', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    vendor_price = fields.Float(string="Vendor Price")
    price_unit = fields.Float(string="Unit Price")

    purchase_line_id = fields.Many2one('purchase.order.line')

    @api.onchange('quantity')
    def _onchange_quantity(self):
        if self.quantity > self.purchase_remain:
            raise UserError("Số lượng trả lại vượt quá số lượng cho phép. Vui lòng thiết lập lại.")


class PurchaseReturnWizard(models.TransientModel):
    _name = "purchase.return.wizard"
    _description = "Purchase Return Wizard"

    @api.model
    def default_get(self, fields):
        res = super(PurchaseReturnWizard, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'purchase.order':
            if len(self.env.context.get('active_ids', list())) > 1:
                raise UserError(_("You may only return one purchase at a time."))
            purchase = self.env['purchase.order'].browse(self.env.context.get('active_id'))
            if purchase.exists():
                res.update({'purchase_id': purchase.id})
        return res

    purchase_id = fields.Many2one('purchase.order')
    purchase_return_lines = fields.One2many('purchase.return.wizard.line', 'wizard_id', 'Lines')
    # move_dest_exists = fields.Boolean('Chained Move Exists', readonly=True)
    # original_location_id = fields.Many2one('stock.location')
    # parent_location_id = fields.Many2one('stock.location')
    company_id = fields.Many2one(related='purchase_id.company_id')
    location_id = fields.Many2one(
        'stock.location', 'Return Location',
        domain="['|', '&', ('return_location', '=', True), ('company_id', '=', False), '&', ('return_location', '=', True), ('company_id', '=', company_id)]")

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        move_dest_exists = False
        purchase_return_lines = [(5,)]
        if self.purchase_id and self.purchase_id.custom_state != 'approved':
            raise UserError(_("You may only return Approved Purchase."))
        # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
        # default values for creation.
        line_fields = [f for f in self.env['stock.return.picking.line']._fields.keys()]
        purchase_return_lines_data_tmpl = self.env['purchase.return.wizard.line'].default_get(line_fields)
        for line in self.purchase_id.order_line:
            if line.received <= 0:
                continue
            if (line.received - line.qty_returned) <= 0:
                continue
            # if move.move_dest_ids:
            #     move_dest_exists = True
            purchase_return_lines_data = dict(purchase_return_lines_data_tmpl)
            purchase_return_lines_data.update(self._prepare_stock_return_purchase_line_vals(line))
            if purchase_return_lines_data.get('purchase_remain', 0) > 0:
                purchase_return_lines.append((0, 0, purchase_return_lines_data))

        if self.purchase_id and not purchase_return_lines:
            raise UserError(_("No products to return (only lines in Done state and not fully returned yet can be returned)."))
        if self.purchase_id:
            self.purchase_return_lines = purchase_return_lines
            # self.move_dest_exists = move_dest_exists
            # self.parent_location_id = self.purchase_id.picking_type_id.warehouse_id and self.purchase_id.picking_type_id.warehouse_id.view_location_id.id or self.purchase_id.location_id.location_id.id
            # self.original_location_id = self.purchase_id.location_id.id
            # location_id = self.purchase_id.partner_id.property_stock_supplier.id
            # if self.purchase_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
            #     location_id = self.purchase_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
            self.location_id = self.purchase_id.location_id.id

    @api.model
    def _prepare_stock_return_purchase_line_vals(self, purchase_line):
        purchase_received = purchase_line.received
        purchase_returned = purchase_line.qty_returned
        exchange_quantity = purchase_line.exchange_quantity
        vendor_price = purchase_line.vendor_price
        price_unit = purchase_line.price_unit
        # quantity = float_round(quantity, precision_rounding=purchase_line.product_id.purchase_uom.rounding)
        return {
            'product_id': purchase_line.product_id.id,
            'purchase_received': purchase_received,
            'purchase_returned': purchase_returned,
            'purchase_remain': purchase_received - purchase_returned,
            'exchange_quantity': exchange_quantity,
            'quantity': 0,
            'vendor_price': vendor_price,
            'price_unit': price_unit,
            'uom_id': purchase_line.purchase_uom.id if purchase_line.purchase_uom else purchase_line.product_id.uom_id.id,
            'purchase_line_id': purchase_line.id
        }

    def _prepare_purchase_default_values(self, line_vals):
        vals = {
            'is_return': True,
            'origin_purchase_id': self.purchase_id.id,
            'order_line': line_vals,
            'location_id': self.purchase_id.location_id.id,
            'picking_type_id': self.purchase_id.picking_type_id.return_picking_type_id.id or self.purchase_id.picking_type_id.id,
            'state': 'draft',
            'custom_state': 'draft',
            'source_document': _("Return of %s") % self.purchase_id.name,
            'dest_address_id': self.purchase_id.partner_id.id
        }
        # TestPickShip.test_mto_moves_return, TestPickShip.test_mto_moves_return_extra,
        # TestPickShip.test_pick_pack_ship_return, TestPickShip.test_pick_ship_return, TestPickShip.test_return_lot
        if self.purchase_id.location_id:
            vals['source_location_id'] = self.purchase_id.location_id.id
        if self.location_id:
            vals['location_id'] = self.location_id.id
        return vals

    def _prepare_purchase_line_default_values(self, return_line):
        vals = {
            'product_id': return_line.product_id.id,
            'description': return_line.product_id.name,
            'product_uom': return_line.uom_id.id,
            'purchase_quantity': return_line.quantity / return_line.exchange_quantity,
            'exchange_quantity': return_line.exchange_quantity,
            'product_qty': return_line.quantity,
            'vendor_price': return_line.vendor_price,
            'price_unit': return_line.vendor_price / return_line.exchange_quantity if return_line.exchange_quantity else 0,
            'origin_po_line_id': return_line.purchase_line_id.id,
            'purchase_uom': return_line.purchase_line_id.purchase_uom.id,
            'taxes_id': [(6, 0, return_line.purchase_line_id.taxes_id.ids)],
            'discount_percent': return_line.purchase_line_id.discount_percent,
            'occasion_code_id': return_line.purchase_line_id.occasion_code_id.id,
            'production_id': return_line.purchase_line_id.production_id.id,
            'account_analytic_id': return_line.purchase_line_id.account_analytic_id.id,
        }
        return vals

    def _create_returns(self):
        line_vals = []
        for return_line in self.purchase_return_lines:
            # TODO : float_is_zero?
            if return_line.quantity:
                # po_line = return_line.purchase_line_id.copy({
                #     'product_id': return_line.product_id.id
                # })
                # po_line.onchange_product_id()
                # po_line.write(self._prepare_purchase_line_default_values(return_line))
                line_vals.append((0, 0, self._prepare_purchase_line_default_values(return_line)))

        new_purchase = self.purchase_id.copy(self._prepare_purchase_default_values(line_vals))
        # for line in new_purchase.order_line:
        #     current_val = line.read(['purchase_quantity', 'exchange_quantity', 'vendor_price', 'price_unit'])
        #     line.onchange_product_id()
        #     line.write(current_val[0])
        #     line.onchange_price_unit()
        picking_type_id = new_purchase.picking_type_id.id
        new_purchase.message_post_with_view('mail.message_origin_link',
            values={'self': new_purchase, 'origin': self.purchase_id},
            subtype_id=self.env.ref('mail.mt_note').id)
        return new_purchase.id, picking_type_id

    def create_returns(self):
        for wizard in self:
            new_purchase_id, pick_type_id = wizard._create_returns()
        # Override the context to disable all the potential filters that could have been set previously
        ctx = dict(self.env.context)
        ctx.update({
            'default_partner_id': self.purchase_id.partner_id.id,
            'search_default_picking_type_id': pick_type_id,
        })
        return {
            'name': _('Returned Purchase'),
            'view_mode': 'form,tree',
            'res_model': 'purchase.order',
            'res_id': new_purchase_id,
            'type': 'ir.actions.act_window',
            'context': ctx,
        }
