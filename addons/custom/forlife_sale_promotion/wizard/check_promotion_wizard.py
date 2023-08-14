# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CheckPromotion(models.TransientModel):
    _name = 'check.promotion.wizard'
    _description = 'Check Promotion wizard'

    message = fields.Char(string="Message")
    voucher_name = fields.Char(string="Voucher gốc")
    voucher_name_change = fields.Char(string="Voucher chỉnh sửa")
    voucher_value = fields.Float(string='Giá trị voucher (Nhanh)')
    voucher_value_change = fields.Float(string='Giá trị voucher chỉnh sửa')

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

        # Thay đổi giá trị Voucher
        if self.voucher_name_change:
            voucher_id = self.env['voucher.voucher'].search([('name', '=', self.voucher_name_change)])
            if not voucher_id:
                raise ValidationError('Voucher %s không tồn tại trong hệ thống, vui lòng kiểm tra lại' % self.voucher_name_change)
            if voucher_id.state not in ['sold', 'valid']:
                raise ValidationError('Trạng thái của Voucher phải là "Đã bán" hoặc "Còn giá trị"')
            active_id = self._context and self._context.get('active_id')
            sale_id = self.env['sale.order'].search([('id', '=', active_id)], limit=1)
            if sale_id:
                sale_id.message_post(body='Voucher thay đổi: %s -> %s' % (sale_id.x_code_voucher, self.voucher_name_change))
                sale_id.x_code_voucher = self.voucher_name_change

        # Thay đổi giá trị Voucher
        if self.voucher_value_change:
            active_id = self._context and self._context.get('active_id')
            sale_id = self.env['sale.order'].search([('id', '=', active_id)], limit=1)
            if sale_id:
                voucher_id = self.env['voucher.voucher'].search([('name', '=', sale_id.x_code_voucher)])
                if voucher_id.price_residual < self.voucher_value_change:
                    raise ValidationError(_("Giá trị voucher (Nhanh) không được vượt quá %s" % "{:0,.0f}".format(voucher_id.price_residual)))
                sale_id.message_post(body='Voucher thay đổi giá trị: %s -> %s' % ("{:0,.0f}".format(sale_id.x_voucher), "{:0,.0f}".format(self.voucher_value_change)))
                sale_id.x_voucher = self.voucher_value_change

        else:
            pass



