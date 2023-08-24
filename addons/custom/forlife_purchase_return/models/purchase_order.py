import datetime

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby
import logging
_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_return = fields.Boolean(string="Is return?", default=False)
    return_purchase_ids = fields.One2many('purchase.order', 'origin_purchase_id', string="Return Purchases", copy=False)
    origin_purchase_id = fields.Many2one('purchase.order', string="Origin Purchase", copy=False)
    count_return_purchase = fields.Integer(compute="_compute_count_return_purchase", store=True, copy=False)
    return_picking_count = fields.Integer("Return Shipment count", compute='_compute_return_picking_count')
    count_invoice_refund = fields.Integer(compute='_compute_count_invoice_refund')

    def _compute_count_invoice_refund(self):
        for rec in self:
            rec.count_invoice_refund = self.env['account.move'].search_count([
                ('purchase_order_product_id', 'in', rec.ids),
                ('move_type', '=', 'in_refund')
            ])

    @api.depends('picking_ids')
    def _compute_return_picking_count(self):
        for order in self:
            order.return_picking_count = len(order.picking_ids)

    @api.onchange('partner_id')
    def _onchange_partner_id_return(self):
        if self.partner_id and self.is_return:
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

    def action_view_invoice_refund(self):
        for order in self:
            invoice_refund = self.env['account.move'].search([
                ('purchase_order_product_id', 'in', order.ids),
                ('move_type', '=', 'in_refund')
            ])
            return {
                'name': _('Hóa đơn nhà cung cấp'),
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', 'in', invoice_refund.ids)],
                'context': {'create': True, 'delete': True, 'edit': True}
            }

    def _prepare_picking(self):
        vals = super(PurchaseOrder, self)._prepare_picking()
        if self.is_return:
            if type(vals) == list:
                for val in vals:
                    val.update({
                        'location_id': self.location_id.id,
                        'location_dest_id': self.partner_id.property_stock_supplier.id,
                        'x_is_check_return': True,
                        'origin': val.get('origin', '') + _(' Return')
                    })
            else:
                vals.update({
                    'location_id': self.location_id.id,
                    'location_dest_id': self.partner_id.property_stock_supplier.id,
                    'x_is_check_return': True,
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
                po.picking_ids.write({
                    'location_id': po.location_id.id,
                    'location_dest_id': po.partner_id.property_stock_supplier.id,
                    'x_is_check_return': True,
                })
        return res

    def action_create_invoice(self, partner_id=False, currency_id=False, exchange_rate=False):
        if len(self) == 1 and self.is_return:
            if self.custom_state != 'approved':
                raise UserError(_('Tạo hóa đơn không hợp lệ!'))
            # Invoice values.
            invoice_vals = self._prepare_invoice()
            invoice_vals.update({
                'purchase_type': self.purchase_type,
                'invoice_date': datetime.now(),
                'exchange_rate': self.exchange_rate,
                'currency_id': self.currency_id.id,
                'move_type': 'in_refund',
            })
            invoice_vals_list = []
            sequence = 10

            order = self.with_company(self.company_id)
            pending_section = None
            picking_ids = []
            if self.purchase_type in ('service', 'asset'):
                self.write({
                    'invoice_status_fake': 'to invoice',
                })
                invoice_relationship = self.env['account.move'].search([('reference', '=', order.name), ('partner_id', '=', order.partner_id.id)])
                # if invoice_relationship:
                if sum(invoice_relationship.invoice_line_ids.mapped('price_subtotal')) == sum(order.order_line.mapped('price_subtotal')):
                    raise UserError(_('Hóa đơn đã được khống chế theo đơn mua hàng!'))
                else:
                    for line in order.order_line:
                        if invoice_relationship:
                            wave = invoice_relationship.invoice_line_ids.filtered(lambda w: str(w.po_id) == str(line.id) and w.product_id.id == line.product_id.id)
                            quantity = sum(wave.mapped('quantity'))
                        else:
                            quantity = 0
                        data_line = self.get_data_line(line, False, sequence, order, quantity)
                        if line.display_type == 'line_section':
                            pending_section = line
                            continue
                        if pending_section:
                            line_vals = pending_section._prepare_account_move_line()
                            line_vals.update(data_line)
                            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            sequence += 1
                            pending_section = None
                        line_vals = line._prepare_account_move_line()
                        line_vals.update(data_line)
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        sequence += 1
                    invoice_vals_list.append(invoice_vals)
            else:
                domain = [('purchase_id', '=', self.id), ('state', '=', 'done'), ('ware_check', '=', False), ('x_is_check_return', '=', True)]
                picking_in = self.env['stock.picking'].search(domain)
                if not picking_in:
                    raise UserError(_('Tất cả các phiếu nhập trả đã được lên hóa đơn đầy đủ! Vui lòng kiểm tra lại'))
                picking_ids = picking_in.ids

                for line in order.order_line:
                    wave = picking_in.move_line_ids_without_package.filtered(lambda w: w.move_id.purchase_line_id.id == line.id and w.product_id.id == line.product_id.id and w.picking_id.x_is_check_return == True)
                    if wave:
                        for wave_item in wave:
                            data_line = self.get_data_line(line, wave_item, sequence, order, quantity=0)
                            if line.display_type == 'line_section':
                                pending_section = line
                                continue
                            if pending_section:
                                line_vals = pending_section._prepare_account_move_line()
                                line_vals.update(data_line)
                                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                sequence += 1
                                pending_section = None
                            line_vals = line._prepare_account_move_line()
                            line_vals.update(data_line)
                            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            sequence += 1
                        invoice_vals_list.append(invoice_vals)

            # 2) group by (company_id, partner_id, currency_id) for batch creation
            new_invoice_vals_list = []
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] = invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'purchase_type': self.purchase_type if len(self) == 1 else 'product',
                    'reference': ', '.join(self.mapped('name')),
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'is_check': True,
                    'purchase_order_product_id': [(6, 0, [self.id])],
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                    'type_inv': self.type_po_cost if self.purchase_type == 'product' else False,
                    'is_check_invoice_tnk': True if (self.env.ref('forlife_pos_app_member.partner_group_1') or self.type_po_cost) and self.purchase_type == 'product' else False,
                    'receiving_warehouse_id': [(6, 0, picking_ids)],
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

            # 3) Create invoices.
            moves = self.env['account.move']
            AccountMove = self.env['account.move'].with_context(default_move_type='in_refund')
            for vals in invoice_vals_list:
                moves |= AccountMove.with_company(vals['company_id']).create(vals)
            for line in moves.invoice_line_ids:
                if line.product_id:
                    account_id = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id
                    line.account_id = account_id

            # 4) Some moves might actually be refunds: convert them if the total amount is negative
            # We do this after the moves have been created since we need taxes, etc. to know if the total
            # is actually negative or not
            return moves
        else:
            return super(PurchaseOrder, self).action_create_invoice(partner_id, currency_id, exchange_rate)

    def get_data_line(self, line, wave_item, sequence, order, quantity):
        ware_name = wave_item.picking_id.name if wave_item.picking_id.name else ''
        exchange_quantity = wave_item.quantity_change if wave_item else line.exchange_quantity
        if quantity:
            qty = line.product_qty - quantity
        else:
            qty = wave_item.qty_done if wave_item else line.product_qty
        quantity_purchased = wave_item.quantity_purchase_done if wave_item else line.purchase_quantity
        data_line = {
            'ware_name': ware_name,
            'po_id': line.id,
            'product_id': line.product_id.id,
            'sequence': sequence,
            'price_subtotal': line.price_subtotal,
            'price_total': line.price_subtotal + line.price_tax,
            'promotions': line.free_good,
            'exchange_quantity': exchange_quantity,
            'quantity': qty,
            'vendor_price': line.vendor_price,
            'warehouse': line.location_id.id,
            'discount': line.discount_percent,
            'event_id': line.event_id.id,
            'work_order': line.production_id.id,
            'account_analytic_id': line.account_analytic_id.id,
            'request_code': line.request_purchases,
            'quantity_purchased': quantity_purchased,
            'discount_value': line.discount,
            'tax_ids': [(6, 0, line.taxes_id.ids)],
            'tax_amount': line.price_tax,
            'product_uom_id': line.product_uom.id,
            'price_unit': line.price_unit,
            'total_vnd_amount': line.price_subtotal * order.exchange_rate,
            'company_id': line.company_id.id,
        }
        return data_line

    def action_view_invoice_new(self):
        if not self.is_return:
            return super(PurchaseOrder, self).action_view_invoice_new()

        for rec in self:
            data_search = self.env['account.move'].search(
                [('reference', '=', rec.name), ('move_type', '=', 'in_refund')]).ids
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', data_search), ('move_type', '=', 'in_refund')],
        }


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    origin_po_line_id = fields.Many2one('purchase.order.line')
    return_line_ids = fields.One2many('purchase.order.line', 'origin_po_line_id', string="Return Lines")

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom',
        'return_line_ids.order_id', 'return_line_ids.order_id.custom_state', 'return_line_ids.move_ids.state')
    def _compute_qty_returned(self):
        for line in self:
            if line.order_id.is_return:
                total = 0.0
                for move in line._get_po_line_moves():
                    if move.state == 'done':
                        # total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')

                        if move._is_purchase_return():
                            if move.to_refund:
                                # total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                                pass
                        elif move.origin_returned_move_id and move.origin_returned_move_id._is_dropshipped() and not move._is_dropshipped_returned():
                            # Edge case: the dropship is returned to the stock, no to the supplier.
                            # In this case, the received quantity on the PO is set although we didn't
                            # receive the product physically in our stock. To avoid counting the
                            # quantity twice, we do nothing.
                            pass
                        else:
                            total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')

                line.qty_returned = total/line.exchange_quantity
            else:
                total = 0.0
                if line.qty_received_method == 'stock_moves':
                    for move in line._get_po_line_moves():
                        if move.state == 'done':
                            if move._is_purchase_return():
                                if move.to_refund:
                                    total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')

                # Include qty of PO return
                return_line = line.return_line_ids.filtered(lambda rl: rl.qty_received)
                total += sum(return_line.mapped('qty_received'))
                line.qty_returned = total/line.exchange_quantity

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_received(self):
        return_lines = self.filtered(lambda order_line: order_line.qty_received_method == 'stock_moves' and order_line.order_id.is_return)
        super(PurchaseOrderLine, self - return_lines)._compute_qty_received()
        for line in return_lines:
            if line.order_id.is_return and line.qty_received_method == 'stock_moves':
                total = 0.0
                for move in line._get_po_line_moves():
                    if move.state == 'done':
                        total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                line._track_qty_received(total)
                line.qty_received = total

    def _prepare_account_move_line(self):
        vals = super(PurchaseOrderLine, self)._prepare_account_move_line()
        if self.order_id.is_return:
            vals.update({
                'vat_tax': self.vat_tax,
                'import_tax': self.import_tax,
                'special_consumption_tax': self.special_consumption_tax,
                'discount': self.discount_percent,
                'discount_value': self.discount,
            })
        return vals

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if self.order_id.is_return:
            location_id = vals['location_dest_id']
            location_dest_id = vals['location_id']
            vals.update({
                'occasion_code_id': self.occasion_code_id.id,
                'work_production': self.production_id.id,
                'account_analytic_id': self.account_analytic_id.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
            })
        return vals
