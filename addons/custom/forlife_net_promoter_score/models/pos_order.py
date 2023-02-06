# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        self.with_delay().create_forlife_comment()
        return res

    def create_forlife_comment(self):
        self.env['forlife.comment'].sudo().create(self.prepare_comment_data())

    def prepare_comment_data(self):
        return dict({
            'question_id': self.env['forlife.question'].search([], limit=1).id,
            'customer_code': self.partner_id.mobile or self.partner_id.phone,
            'branch': self.config_id.store_id.brand_id.code,
            'invoice_number': self.pos_reference,
            'invoice_date': self.date_order,
            'status': -1,
        })
