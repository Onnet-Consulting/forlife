# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round, float_is_zero, float_compare

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _domain_reason_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

    free_good = fields.Boolean(string="Hàng tặng")
    purchase_uom = fields.Many2one('uom.uom', string="Đơn vị mua")
    quantity_change = fields.Float(string="Số lượng quy đổi")
    quantity_purchase_done = fields.Float(string="Số lượng mua hoàn thành")
    occasion_code_id = fields.Many2one('occasion.code', 'Occasion Code')
    work_production = fields.Many2one('forlife.production', string='Lệnh sản xuất',
                                      domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")
    reason_id = fields.Many2one('stock.location', domain=_domain_reason_id)
    is_production_order = fields.Boolean(default=False, compute='compute_production_order')
    is_amount_total = fields.Boolean(default=False, compute='compute_production_order')

    @api.depends('reason_id')
    def compute_production_order(self):
        for rec in self:
            rec.is_production_order = rec.reason_id.is_work_order
            rec.is_amount_total = rec.reason_id.is_price_unit

    @api.onchange('quantity_change', 'quantity_purchase_done')
    def onchange_quantity_purchase_done(self):
        self.qty_done = self.quantity_purchase_done * self.quantity_change

    @api.onchange('qty_done')
    def onchange_qty_done(self):
        self.quantity_purchase_done = self.qty_done/self.quantity_change


class StockMove(models.Model):
    _inherit = 'stock.move'

    free_good = fields.Boolean(string="Hàng tặng")
    quantity_change = fields.Float(string="Số lượng quy đổi")
    quantity_purchase_done = fields.Float(string="Số lượng mua hoàn thành")

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.origin_returned_move_id or not self.purchase_line_id or not self.product_id.id:
            return super(StockMove, self)._get_price_unit()
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        line = self.purchase_line_id
        order = line.order_id
        received_qty = line.qty_received
        if self.state == 'done':
            received_qty -= self.product_uom._compute_quantity(self.quantity_done, line.product_uom,
                                                               rounding_method='HALF-UP')
        if float_compare(line.qty_invoiced, received_qty, precision_rounding=line.product_uom.rounding) > 0:
            move_layer = line.move_ids.stock_valuation_layer_ids
            invoiced_layer = line.invoice_lines.stock_valuation_layer_ids
            receipt_value = sum(move_layer.mapped('value')) + sum(invoiced_layer.mapped('value'))
            invoiced_value = 0
            invoiced_qty = 0
            for invoice_line in line.invoice_lines:
                if invoice_line.tax_ids:
                    invoiced_value += invoice_line.tax_ids.with_context(round=False).compute_all(
                        invoice_line.price_unit, currency=invoice_line.account_id.currency_id,
                        quantity=invoice_line.quantity)['total_void']
                else:
                    invoiced_value += invoice_line.price_unit * invoice_line.quantity
                invoiced_qty += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity,
                                                                              line.product_id.uom_id)
            # TODO currency check
            remaining_value = invoiced_value - receipt_value
            # TODO qty_received in product uom
            remaining_qty = invoiced_qty - line.product_uom._compute_quantity(received_qty, line.product_id.uom_id)
            price_unit = float_round(remaining_value / remaining_qty, precision_digits=price_unit_prec)
        else:
            price_unit = line.price_unit - (line.price_unit * line.discount_percent / 100)
            if line.taxes_id:
                qty = line.product_qty or 1
                price_unit = \
                line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id,
                                                                    quantity=qty)['total_void']
                price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            # The date must be today, and not the date of the move since the move move is still
            # in assigned state. However, the move date is the scheduled date until move is
            # done, then date of actual move processing. See:
            # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self),
                round=False)
        return price_unit
