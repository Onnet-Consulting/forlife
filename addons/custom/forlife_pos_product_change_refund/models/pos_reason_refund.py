# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class POSReasonRefund(models.Model):
    _name = 'pos.reason.refund'
    _description = 'Reason Refund for POS'

    name = fields.Char('Name', required=True)
    brand_id = fields.Many2one('res.brand', 'Brand', required=True)
    is_refund_points = fields.Boolean('Trả hàng hoàn điểm', default=False)

    def unlink(self):
        exist_order_line_ids = self.env['pos.order.line'].sudo().search_count([('reason_refund_id', 'in', self.ids)])
        if not exist_order_line_ids:
            return super(POSReasonRefund, self).unlink()
        raise ValidationError(_('Cannot delete Reason Refund used in POS Order'))

