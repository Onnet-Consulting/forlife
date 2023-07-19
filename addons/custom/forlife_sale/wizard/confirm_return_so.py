from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import UserError
from odoo.tests import Form

class ConfirmReturnSo(models.Model):
    _name = 'confirm.return.so'
    _description = "Confirm Return SO"

    name = fields.Char('Xác nhận trả hàng', default='Xác nhận trả hàng')
    origin = fields.Many2one('sale.order')
    line_ids = fields.One2many('confirm.return.so.line', 'master_id', string='Chọn phiếu trả hàng', copy=False)


class ConfirmReturnSoLine(models.Model):
    _name = 'confirm.return.so.line'
    _description = "Confirm Return SO details"

    master_id = fields.Many2one('confirm.return.so', 'Master data')
    picking_id = fields.Many2one('stock.picking', 'Phiếu kho')
    picking_name = fields.Char('Phiếu kho')
    state = fields.Char('Trạng thái phiếu kho')

    def action_return(self):
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(active_ids=self.picking_id.ids, active_id=self.picking_id.id,
                                                          active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        ctx = {
            'x_return': True,
            'so_return': self.master_id.origin.id,
            'picking_id': self.picking_id.id,
            'wizard_line_id': self.id
        }
        return {
            'name': _('Trả hàng phiếu %s' % (self.picking_id.name)),
            'view_mode': 'form',
            'res_model': 'stock.return.picking',
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'res_id': return_wiz.id,
            'context': ctx,
            'target': 'new'
        }
