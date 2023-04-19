# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class POSCompensatePoint(models.TransientModel):
    _name = 'pos.compensate.point.order'
    _description = "Compensate Point Wizard"

    order_ids = fields.Many2many(
        'pos.order', default=lambda self: self.env.context.get('active_ids'))
    reason = fields.Text(default='')

    def apply(self):
        list_name_pos = []
        for rec in self.order_ids:
            pos_order = self.env['pos.order'].browse(rec.id)
            brand_pos_id = pos_order.config_id.store_id.brand_id.id
            if not pos_order.partner_id:
                raise UserError(_('Đơn hàng {} chưa chọn khách hàng !'.format(pos_order.name)))
            if (brand_pos_id == self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id and self.env.ref(
                    'forlife_pos_app_member.res_partner_retail_format_app', raise_if_not_found=False).id not in pos_order.partner_id.retail_type_ids.ids) or (
                    brand_pos_id == self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id and self.env.ref(
                'forlife_pos_app_member.res_partner_retail_tokyolife_app', raise_if_not_found=False).id not in pos_order.partner_id.retail_type_ids.ids):
                raise UserError(_('Khách hàng chưa cài app!'))
            if not pos_order.allow_compensate_point:
                list_name_pos.append(pos_order.name)
        if list_name_pos:
            raise UserError(_(f"Các đơn hàng sau đã được tích điểm : {', '.join(list_name_pos)}"))

        self.order_ids.btn_compensate_points_all(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}
