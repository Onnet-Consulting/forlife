# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import api, fields, models, _


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        for line in self.product_return_moves:
            if line.quantity > line.move_id.product_qty:
                raise UserError(_('Sản phẩm %s đã vượt số lượng yêu cầu nhập hàng trả' % (
                    line.product_id.name)))
        res = super().create_returns()
        return res

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

    def _create_returns(self):
        res = super()._create_returns()
        if self._context.get('so_return'):
            new_picking_id, pick_type_id = res
            self._cr.commit()
            sql = f"""
                    update stock_picking
                    set sale_id = {self._context.get('so_return')}
                    where id = {new_picking_id}
                """
            self._cr.execute(sql)
        return res

    def x_return(self):
        for wizard in self:
            new_picking_id, pick_type_id = wizard._create_returns()
        return True

    def create_sale_order(self):
        if self._context.get('x_return'):
            picking_id = self.env['stock.picking'].browse(self._context.get('picking_id'))
        else:
            picking_id = self.env['stock.picking'].browse(self._context.get('active_id'))
        origin = self.env['sale.order'].search([('name', '=', picking_id.origin)])
        vals = {
            'partner_id': picking_id.partner_id.id,
            'x_sale_type': picking_id.move_ids[0].product_id.product_type,
            'x_origin': origin.id if origin else None,
            'x_is_exchange': True
        }
        so_id = self.env['sale.order'].create(vals)
        return so_id
