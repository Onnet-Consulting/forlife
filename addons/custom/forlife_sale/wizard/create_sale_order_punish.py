from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import UserError


class CreateSaleOrderPunish(models.Model):
    _name = 'create.sale.order.punish'

    x_partner_id = fields.Many2one('res.partner', string='Khách hàng')

    def create_invoice_punish(self):
        order_punish_id = self.env['sale.order'].browse(self._context.get('active_id')).copy()
        order_punish_id.partner_id = self.x_partner_id
        order_punish_id.state = 'draft'
        for line in order_punish_id.order_line:
            line._compute_price_unit()
        return {
            'name': _(order_punish_id.name),
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_id': self.env.ref('sale.view_order_form').id,
            'target': 'current',
            'create': 'True',
            'res_id': order_punish_id.id
        }