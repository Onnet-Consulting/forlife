# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta


class ResUtility(models.AbstractModel):
    _inherit = 'res.utility'

    @api.model
    def get_customer_information_with_brand(self, phone_number, brand_code):
        customer = self.env['res.partner'].search([('phone', '=', phone_number)], limit=1)
        if not customer:
            return []
        total_points_available = customer.total_points_available_format if brand_code == 'FMT' else customer.total_points_available_forlife
        reset_day_of_point = customer.reset_day_of_point_format if brand_code == 'FMT' else customer.reset_day_of_point_forlife
        result = {
            'id': customer.id or 0,
            'name': customer.name or '',
            'phone': customer.phone or '',
            'barcode': customer.barcode or '',
            'birthday': customer.birthday.strftime('%d/%m/%Y') if customer.birthday else '',
            'email': customer.email or '',
            'gender': customer.gender or '',
            'total_points_available': total_points_available or 0,
            'reset_day_of_point': (reset_day_of_point + timedelta(hours=7)).strftime('%d/%m/%Y') if reset_day_of_point else '',
            'TotalRevenue': 0,
            'SubRevenue': 0,
            'NextClass': '',
            'DateRevenue': '',
        }
        partner_card_rank = customer.card_rank_ids.filtered(lambda x: x.brand_id.code == brand_code)
        result.update({
            'customerClassId': partner_card_rank.card_rank_id.id or 0,
            'customerClass': partner_card_rank.card_rank_id.name or '',
        })
        partner_card_rank_line = partner_card_rank.line_ids[:1]
        if partner_card_rank_line:
            next_cr_program = self.env['member.card'].search([('min_turnover', '>', partner_card_rank_line.program_cr_id.min_turnover)], order='min_turnover', limit=1)
            if next_cr_program:
                current_date = fields.Datetime.now()
                begin_date = current_date - timedelta(days=next_cr_program.time_set_rank)
                pcr_check = partner_card_rank.line_ids.filtered(lambda f: f.order_date >= begin_date)
                total_revenue = sum(pcr_check.mapped('value_to_upper'))
                sub_revenue = next_cr_program.min_turnover - total_revenue
                if pcr_check:
                    date_revenue = pcr_check[-1].order_date + timedelta(days=next_cr_program.time_set_rank, hours=7)
                else:
                    date_revenue = current_date + timedelta(days=next_cr_program.time_set_rank, hours=7)
                result.update({
                    'TotalRevenue': total_revenue,
                    'SubRevenue': int(sub_revenue),
                    'NextClass': next_cr_program.card_rank_id.name or '',
                    'DateRevenue': date_revenue.strftime('%d/%m/%Y') or '',
                })
        return [result]
