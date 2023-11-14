# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ChooseTypeOfMoveWizard(models.TransientModel):
    _name = "choose.type.of.move.wizard"
    _description = 'Chọn loại bút toán'

    type = fields.Selection(string='Chọn loại', selection=[('bt_chenh_lech', 'Tạo bút toán chênh lệch'), ('bt_thu_tien', 'Tạo bút toán thu tiền')], required=True)

    def btn_apply(self):
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        record = self.env[active_model].browse(active_id)
        return record.with_context(move_post_type=self.type).action_post()
