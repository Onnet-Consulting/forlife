# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Exchange')
    manual_currency_exchange_rate = fields.Float('Rate', digits=(12, 6))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            if line.taxes_id:
                qty = line.product_qty or 1
                price_unit = \
                line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id,
                                                                    quantity=qty)['total_void']
                price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if self.picking_id and self.picking_id.active_manual_currency_rate and self.picking_id.apply_manual_currency_exchange:
                price_unit = price_unit / (1 / self.picking_id.manual_currency_exchange_rate)
            else:
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self),
                    round=False)
            return price_unit
        return super(StockMove, self)._get_price_unit()