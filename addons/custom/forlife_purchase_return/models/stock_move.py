# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round

class StockMove(models.Model):
    _inherit = 'stock.move'

    include_move_id = fields.Many2one('stock.move')

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super(StockMove, self)._prepare_move_line_vals(quantity, reserved_quant)
        if self.purchase_line_id:
            vals.update({
                'purchase_uom': self.purchase_line_id.purchase_uom.id,
                'occasion_code_id': self.purchase_line_id.occasion_code_id.id,
                'work_production': self.purchase_line_id.production_id.id,
                'account_analytic_id': self.purchase_line_id.account_analytic_id.id,
            })
            if self.picking_id.x_is_check_return:
                vals.update({
                    'quantity_change': self.purchase_line_id.exchange_quantity,
                    'qty_done': self.product_qty
                })
        return vals

    def _get_price_unit(self):
        self.ensure_one()
        if (self.origin_returned_move_id and self.purchase_line_id) or self.purchase_line_id.order_id.is_return:
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            line = self.purchase_line_id
            order = line.order_id

            if self.origin_returned_move_id:
                price_unit = self.origin_returned_move_id.purchase_line_id.price_unit
            else:
                price_unit = line.product_id.standard_price if not line.origin_po_line_id else line.origin_po_line_id.price_unit

            if line.taxes_id:
                qty = line.product_qty or 1
                price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=qty)['total_void']
                price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                price_unit = order.currency_id._convert(price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self), round=False)

            return price_unit

        return super(StockMove, self)._get_price_unit()

    def _get_in_svl_vals(self, forced_quantity):
        return_move = self.filtered(lambda m: m.purchase_line_id and m.purchase_line_id.order_id.is_return)
        svl_vals_list = super(StockMove, self - return_move)._get_in_svl_vals(forced_quantity)

        for move in return_move:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = move.product_id.standard_price
            if move.product_id.cost_method != 'standard':
                unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            if move.picking_id.other_import and move.picking_id.location_id.is_price_unit:
                unit_cost = move.amount_total / move.previous_qty if move.previous_qty != 0 else 0
            return_quantity = forced_quantity or valued_quantity
            svl_vals = move.product_id._prepare_in_svl_vals(-return_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return svl_vals_list

    def _account_entry_move(self, qty, description, svl_id, cost):
        am_vals = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        if 'extend_account_npl' in self._context and self.include_move_id and len(am_vals) == 1:
            include_move_id = self.include_move_id
            account_1561 = include_move_id.product_id.categ_id.property_stock_valuation_account_id.id

            if self.reason_id.type_other == 'incoming':
                debit_account_id = self.reason_id.x_property_valuation_out_account_id.id
                credit_account_id = account_1561
                line_ids = am_vals[0].get('line_ids')

                # FIXME: find true logic
                if len(line_ids) == 2:
                    for line in line_ids:
                        if line[2]['balance'] < 0:
                            credit = -line[2]['balance']
                        else:
                            debit = line[2]['balance']
                else:
                    value = self._get_price_unit() * self.quantity_done
                    credit = value
                    debit = value

                # Other debit line account
                line_ids += [(0, 0, {
                    'account_id': debit_account_id,
                    'name': self.product_id.name,
                    'debit': debit,
                    'credit': 0,
                })]
                # Other credit line account
                line_ids += [(0, 0, {
                    'account_id': credit_account_id,
                    'name': include_move_id.product_id.name,
                    'debit': 0,
                    'credit': credit,
                })]
                am_vals[0]['line_ids'] = line_ids

        return am_vals