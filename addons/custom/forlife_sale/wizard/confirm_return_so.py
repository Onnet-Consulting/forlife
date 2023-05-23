from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import UserError


class ConfirmReturnSo(models.Model):
    _name = 'confirm.return.so'

    picking_ids = fields.One2many('confirm.return.so.line', 'master_id', string='Thông tin phiếu trả hàng', copy=False)


class ConfirmReturnSoLine(models.Model):
    _name = 'confirm.return.so.line'

    master_id = fields.Many2one('confirm.return.so', 'Master data')
    test = fields.Char('test')
    test1 = fields.Char('test1')