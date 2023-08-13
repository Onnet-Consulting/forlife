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
            wizard_line_id = self.env['confirm.return.so.line'].search(
                [('id', '=', self._context.get('wizard_line_id'))])
            wizard_line_id.state = 'Đã trả'
        return res

    def x_return(self):
        for wizard in self:
            new_picking_id, pick_type_id = wizard._create_returns()
        return True

    def create_sale_order(self):
        # validate with case from SO and from Stock_picking
        if self._context.get('x_return'):
            picking_id = self.env['stock.picking'].browse(self._context.get('picking_id'))
            origin = self._context.get('so_return')
        else:
            picking_id = self.env['stock.picking'].browse(self._context.get('active_id'))
            so_origin = self.env['sale.order'].search([('name', '=', picking_id.origin)])
            origin = so_origin.id if so_origin else None
        vals = {
            'partner_id': picking_id.partner_id.id,
            'x_sale_type': picking_id.move_ids[0].product_id.product_type,
            'x_origin': origin,
            'x_is_exchange': True
        }
        so_id = self.env['sale.order'].create(vals)
        return so_id
    
    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        res = super(ReturnPicking, self)._prepare_stock_return_picking_line_vals_from_move(stock_move)
        context = self.env.context
        SaleOL = self.env['sale.order.line']
        SaleO = self.env['sale.order']
        if self.picking_id.sale_id:
            if stock_move.sale_line_id:
                if 'so_return' in context and context.get('so_return'):
                    so_return = SaleO.browse(context.get('so_return'))
                    new_sale_line_id = SaleOL.search([('product_id','=',stock_move.product_id.id),('order_id','=',so_return)],limit=1)
                    quantity_returned = new_sale_line_id.product_uom_qty
                    res.update({
                        'quantity': quantity_returned,
                    })
        return res
