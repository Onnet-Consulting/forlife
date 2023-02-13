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
        current_date = fields.Datetime.now()
        brand_id = self.config_id.store_id.brand_id
        question_id = self.env['forlife.question'].search([('company_id', '=', self.env.company.id), ('brand_id', '=', brand_id.id), ('start_date', '<=', current_date), ('finish_date', '>=', current_date)], limit=1)
        if not question_id:
            raise ValueError(_('Question not found !'))
        return dict({
            'question_id': question_id.id,
            'customer_code': self.partner_id.phone,
            'customer_name': self.partner_id.name,
            'brand': brand_id.code,
            'store_name': self.config_id.store_id.name,
            'store_code': self.config_id.store_id.code,
            'areas': 'S1', # fixme areas from warehouse self.config_id.store_id.warehouse_id.areas
            'invoice_number': self.pos_reference,
            'invoice_date': self.date_order,
            'status': -1,
        })
