# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def exchange_returns(self):
        self.create_returns()
        so_id = self.create_sale_order()

    def create_sale_order(self):
        picking_id = self.env['stock.picking'].browse(self._context.get('active_id'))
        origin = self.env['sale.order'].search([('name', '=', picking_id.origin)])
        vals = {
            'partner_id': picking_id.partner_id.id,
            'x_sale_type': picking_id.move_ids[0].product_id.product_type,
            'x_origin': origin.id if origin else None,
            'x_is_return': True
        }
        so_id = self.env['sale.order'].create(vals)
        origin.x_sale_return_ids = [(4, so_id.id)]
        return so_id

