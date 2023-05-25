from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import UserError


class ConfirmReturnSo(models.Model):
    _name = 'confirm.return.so'

    line_ids = fields.One2many('confirm.return.so.line', 'master_id', string='Chọn phiếu trả hàng', copy=False)


class ConfirmReturnSoLine(models.Model):
    _name = 'confirm.return.so.line'

    master_id = fields.Many2one('confirm.return.so', 'Master data')
    picking_id = fields.Many2one('stock.picking', 'Phiếu kho')
    picking_name = fields.Char('Phiếu kho')
    state = fields.Char('Trạng thái')

    def action_refuse(self):
        if self.picking_id.state != 'done':
            raise UserError(_('Đơn giao hàng chưa hoàn thành'))
        if self.picking_id.state == 'done':
            self.picking_id = 1
        self.state = 'Đã trả'
        print(111111111)
        # return {
        #     'name': _('Xác nhận trả hàng'),
        #     'view_mode': 'form',
        #     'res_model': 'confirm.return.so',
        #     'type': 'ir.actions.act_window',
        #     'views': [(False, 'form')],
        #     'res_id': self.master_id.id,
        #     'target': 'current'
        # }
