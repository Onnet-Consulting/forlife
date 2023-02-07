# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


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
        return dict({
            'question_id': self.env['forlife.question'].search([('company_id', '=', self.env.company.id), ('brand_id', '=', brand_id.id), ('start_date', '<=', current_date), ('finish_date', '>=', current_date)], limit=1).id,
            'customer_code': self.partner_id.phone,
            'customer_name': self.partner_id.name,
            'brand': brand_id.code,
            'branch': self.config_id.store_id.name,
            'invoice_number': self.pos_reference,
            'invoice_date': self.date_order,
            'status': -1,
        })
