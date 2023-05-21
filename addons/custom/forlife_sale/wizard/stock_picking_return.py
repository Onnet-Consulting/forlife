# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def exchange_returns(self):
        self.create_returns()
        so_id = self.create_sale_order()
        return {
            'name': _(so_id.name),
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_id': self.env.ref('sale.view_order_form').id,
            'target': 'current',
            'create': 'True',
            'res_id': so_id.id
        }

    def create_sale_order(self):
        picking_id = self.env['stock.picking'].browse(self._context.get('active_id'))
        origin = self.env['sale.order'].search([('name', '=', picking_id.origin)])
        vals = {
            'partner_id': picking_id.partner_id.id,
            'x_sale_type': picking_id.move_ids[0].product_id.product_type,
            'x_origin': origin.id if origin else None,
        }
        so_id = self.env['sale.order'].create(vals)
        return so_id

