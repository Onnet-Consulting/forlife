from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


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
    quantity = fields.Integer("Quantity")
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    vendor_price = fields.Float(string="Vendor Price")
    price_unit = fields.Float(string="Unit Price")
    purchase_line_id = fields.Many2one('purchase.order.line')
    is_selected = fields.Boolean(string='Selected')

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
    company_id = fields.Many2one(related='purchase_id.company_id')
    location_id = fields.Many2one(
        'stock.location', 'Return Location',
        domain="['|', '&', ('return_location', '=', True), ('company_id', '=', False), '&', ('return_location', '=', True), ('company_id', '=', company_id)]")
    selected_all = fields.Boolean(string='Selected all')

    @api.onchange('selected_all')
    def onchange_selected_all(self):
        self.purchase_return_lines.write({
            'is_selected': self.selected_all
        })

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        purchase_return_lines = []
        if self.purchase_id and self.purchase_id.custom_state != 'approved':
            raise UserError(_("You may only return Approved Purchase."))
        # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
        # default values for creation.
        line_fields = [f for f in self.env['stock.return.picking.line']._fields.keys()]
        purchase_return_lines_data_tmpl = self.env['purchase.return.wizard.line'].default_get(line_fields)
        for line in self.purchase_id.order_line:
            # Tính toán số lượng đã nhận
            qty_received = 0
            moves = line.move_ids.filtered(lambda m: m.product_id == line.product_id and m.state == 'done')
            for move in moves:
                if move._is_purchase_return():
                    if move.to_refund:
                        pass
                elif move.origin_returned_move_id and move.origin_returned_move_id._is_dropshipped() and not move._is_dropshipped_returned():
                    pass
                else:
                    qty_received += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')

            if qty_received == 0 or (qty_received - line.qty_returned) <= 0:
                continue

            purchase_return_lines_data = dict(purchase_return_lines_data_tmpl)
            purchase_return_lines_data.update(self._prepare_stock_return_purchase_line_vals(line, qty_received))
            if purchase_return_lines_data.get('purchase_remain', 0) > 0:
                purchase_return_lines.append((0, 0, purchase_return_lines_data))

        if self.purchase_id and not purchase_return_lines:
            raise UserError(_("Tất cả các sản phẩm của đơn đã được trả hết, vui lòng kiểm tra lại!"))
        if self.purchase_id:
            self.purchase_return_lines = purchase_return_lines
            self.location_id = self.purchase_id.location_id.id

    @api.model
    def _prepare_stock_return_purchase_line_vals(self, purchase_line, qty_received):
        purchase_received = qty_received/purchase_line.exchange_quantity
        purchase_returned = purchase_line.qty_returned/purchase_line.exchange_quantity
        exchange_quantity = purchase_line.exchange_quantity
        vendor_price = purchase_line.vendor_price
        price_unit = purchase_line.price_unit
        return {
            'product_id': purchase_line.product_id.id,
            'purchase_received': purchase_received,
            'purchase_returned': purchase_returned,
            'purchase_remain': purchase_received - purchase_returned,
            'exchange_quantity': exchange_quantity,
            'quantity': 0,
            'vendor_price': vendor_price,
            'price_unit': price_unit,
            'uom_id': purchase_line.purchase_uom.id,
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
        if self.purchase_id.location_id:
            vals['source_location_id'] = self.purchase_id.location_id.id
        if self.location_id:
            vals['location_id'] = self.location_id.id
        return vals

    def _prepare_purchase_line_default_values(self, return_line):
        if return_line.purchase_line_id.discount_percent:
            discount = return_line.purchase_line_id.discount_percent * return_line.purchase_line_id.price_unit * return_line.quantity * 0.01
            readonly_discount = True
        else:
            readonly_discount = False
            discount = 0
        price_unit = return_line.vendor_price / return_line.exchange_quantity if return_line.exchange_quantity and return_line.vendor_price else return_line.purchase_line_id.price_unit
        location_id = self.location_id.id if self.location_id else (return_line.purchase_line_id.location_id.id or return_line.purchase_line_id.order_id.location_id.id)
        purchase_quantity = return_line.quantity

        production_data = []
        for material_line_id in return_line.purchase_line_id.purchase_order_line_material_line_ids:
            production_data.append((0, 0, {
                'product_id': material_line_id.product_id.id,
                'uom': material_line_id.uom.id,
                'production_order_product_qty': material_line_id.production_order_product_qty,
                'production_line_product_qty': return_line.purchase_line_id.product_qty,
                'production_line_price_unit': material_line_id.production_line_price_unit,
                'price_unit': material_line_id.price_unit if material_line_id.product_id.x_type_cost_product else 0,
                'product_qty': (material_line_id.product_qty/return_line.purchase_line_id.product_qty) * return_line.quantity,
                'is_from_po': True,
                'compute_flag': False,
            }))

        vals = {
            'product_id': return_line.product_id.id,
            'description': return_line.product_id.name,
            'product_uom': return_line.uom_id.id,
            'purchase_quantity': purchase_quantity,
            'exchange_quantity': return_line.exchange_quantity,
            'product_qty': return_line.quantity * return_line.exchange_quantity,
            'vendor_price': return_line.vendor_price,
            'price_unit': price_unit,
            'origin_po_line_id': return_line.purchase_line_id.id,
            'purchase_uom': return_line.purchase_line_id.purchase_uom.id,
            'taxes_id': [(6, 0, return_line.purchase_line_id.taxes_id.ids)],
            'discount_percent': return_line.purchase_line_id.discount_percent,
            'discount': discount,
            'readonly_discount': readonly_discount,
            'occasion_code_id': return_line.purchase_line_id.occasion_code_id.id,
            'production_id': return_line.purchase_line_id.production_id.id,
            'account_analytic_id': return_line.purchase_line_id.account_analytic_id.id,
            'receive_date': return_line.purchase_line_id.receive_date,
            'location_id': location_id,
            'import_tax': return_line.purchase_line_id.import_tax,
            'special_consumption_tax': return_line.purchase_line_id.special_consumption_tax,
            'vat_tax': return_line.purchase_line_id.vat_tax,
            'purchase_order_line_material_line_ids': production_data,
        }
        return vals

    def _create_returns(self):
        line_vals = []
        for return_line in self.purchase_return_lines.filtered(lambda x: x.is_selected):
            # TODO : float_is_zero?
            if return_line.quantity:
                line_vals.append((0, 0, self._prepare_purchase_line_default_values(return_line)))

        new_purchase = self.purchase_id.copy(self._prepare_purchase_default_values(line_vals))
        picking_type_id = new_purchase.picking_type_id.id
        new_purchase.message_post_with_view('mail.message_origin_link',
            values={'self': new_purchase, 'origin': self.purchase_id},
            subtype_id=self.env.ref('mail.mt_note').id)
        return new_purchase.id, picking_type_id

    def create_returns(self):
        line_selected = self.purchase_return_lines.filtered(lambda x: x.is_selected)
        if not line_selected:
            raise ValidationError(_('Please select at least 1 line to create an PO return!'))
        if line_selected.filtered(lambda x: x.quantity == 0):
            raise ValidationError(_('Please input quantity greater than 0 in line selected!'))
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
