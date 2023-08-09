# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta


# ["id", "name", "phone", "barcode", "birthday", "email", "gender", "total_points_available_format", "reset_day_of_point_format"],
# "customerClassId"//id hạng hiện tại,"TotalRevenue"//DT hiện tại,"SubRevenue" // DT cần lên hạng,"NextClass"//string : tên hạng tiếp theo,"DateRevenue" // ngày cần đạt được]
class ResUtility(models.AbstractModel):
    _inherit = 'res.utility'

    @api.model
    def get_customer_card_rank_information(self, phone_number, brand_code):
        customer = self.env['res.partner'].search([('phone', '=', phone_number)], limit=1)
        total_points_available = customer.total_points_available_format if brand_code == 'FMT' else customer.total_points_available_forlife
        reset_day_of_point = customer.reset_day_of_point_format if brand_code == 'FMT' else customer.reset_day_of_point_forlife
        result = {
            'id': customer.id or None,
            'name': customer.name or None,
            'phone': customer.phone or None,
            'barcode': customer.barcode or None,
            'birthday': customer.birthday.strftime('%d/%m/%Y') if customer.birthday else None,
            'email': customer.email or None,
            'gender': customer.gender or None,
            'total_points_available': total_points_available or 0,
            'reset_day_of_point': (reset_day_of_point + timedelta(hours=7)).strftime('%d/%m/%Y %H:%M:%S') if reset_day_of_point else None,
            'customerClassId': None,
            'customerClass': None,
            'TotalRevenue': None,
            'SubRevenue': None,
            'NextClass': None,
            'DateRevenue': None,
        }
        partner_card_rank = customer.card_rank_ids.filtered(lambda x: x.brand_id.code == brand_code)
        result.update({
            'customerClassId': partner_card_rank.card_rank_id.id or None,
            'customerClass': partner_card_rank.card_rank_id.name or None,
            'TotalRevenue': partner_card_rank.accumulated_sales or 0,
        })
        partner_card_rank_line = partner_card_rank.line_ids and partner_card_rank.line_ids[0] or False
        if partner_card_rank_line:
            next_cr_program = self.env['member.card'].search([('min_turnover', '>', partner_card_rank_line.program_cr_id.min_turnover)], order='min_turnover', limit=1)
        return [result]
