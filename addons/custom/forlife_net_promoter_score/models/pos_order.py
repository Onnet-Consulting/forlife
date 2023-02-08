# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import json


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        self.with_delay().create_forlife_comment()
        return res

    def create_forlife_comment(self):
        fl_comment = self.env['forlife.comment'].sudo().create(self.prepare_comment_data())
        if fl_comment:
            fl_comment.with_delay().push_notification_to_app(self.partner_id.phone, self.config_id.store_id.brand_id.code)

    def prepare_comment_data(self):
        current_date = fields.Datetime.now()
        brand_id = self.config_id.store_id.brand_id
        question_id = self.env['forlife.question'].search([('company_id', '=', self.env.company.id), ('brand_id', '=', brand_id.id), ('start_date', '<=', current_date), ('finish_date', '>=', current_date)], limit=1)
        if not question_id:
            raise ValueError(_('Question not found !'))
        question_detail = {
            'header': question_id.header,
            'question1': question_id.question1,
            'sub_quest1': question_id.sub_quest1,
            'sub_quest2': question_id.sub_quest2,
            'question2': question_id.question2,
            'success1': question_id.success1,
            'success2': question_id.success2,
            'success3': question_id.success3,
            'banner': question_id.banner,
            'icon': question_id.icon,
        }
        return dict({
            'question_id': question_id.id,
            'customer_code': self.partner_id.phone,
            'customer_name': self.partner_id.name,
            'brand': brand_id.code,
            'branch': self.config_id.store_id.name,
            'invoice_number': self.pos_reference,
            'invoice_date': self.date_order,
            'status': -1,
            'question_detail': question_detail,
        })
