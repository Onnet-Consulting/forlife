# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class CheckPromotion(models.TransientModel):
    _name = 'check.promotion.wizard'

    message = fields.Char(String="Message")

    # wizard kiểm tra CTKM, cập nhật lại trạng thái cho đơn hàng
    @api.model
    def default_get(self, fields_list):
        active_id = self._context and self._context.get('active_id')
        sale_id = self.env['sale.order'].search([('id', '=', active_id)], limit=1)
        sale_id.write({'state': 'check_promotion'})
        if self._context.get('default_message'):
            self = self.with_context(default_message=self._context.get('default_message'))
        return super(CheckPromotion, self).default_get(fields_list)

    def action_ok(self):
        pass



