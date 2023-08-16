# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import timedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        invoices = self.filtered(lambda m: m.state == 'posted')
        for invoice in invoices:
            invoice.update_partner_card_rank_with_nhanh_order()
        return res

    def update_partner_card_rank_with_nhanh_order(self):
        self.ensure_one()
        sale_id = self.line_ids.sale_line_ids.order_id
        sale_id = sale_id and sale_id[0] or sale_id
        brand_id = sale_id.x_location_id.warehouse_id.brand_id
        member_cards = self.env['member.card'].get_member_card_by_date(self.invoice_date, brand_id.id)
        if not member_cards:
            return False
        partner_card_rank = sale_id.order_partner_id.card_rank_ids.filtered(lambda f: f.brand_id.id == brand_id.id)
        if partner_card_rank:
            new_rank = partner_card_rank.card_rank_id
            for program in member_cards:
                if sale_id.order_partner_id.group_id.id == program.customer_group_id.id and \
                        (sale_id.order_partner_id.retail_type_ids and any(retail_type in program.partner_retail_ids for retail_type in sale_id.order_partner_id.retail_type_ids)):
                    value_to_upper_order = self.amount_residual - sale_id.x_voucher
                    total_value_to_up = value_to_upper_order + sum(partner_card_rank.line_ids.filtered(lambda f: f.order_date.date() >= (self.invoice_date - timedelta(days=program.time_set_rank))).mapped('value_to_upper'))
                    if new_rank.priority >= program.card_rank_id.priority:
                        self.env['partner.card.rank.line'].create_partner_card_rank_detail(False, self, partner_card_rank.id, value_to_upper_order, new_rank.id, new_rank.id, total_value_to_up, program.id)
                        break
                    else:
                        if total_value_to_up >= program.min_turnover:
                            self.env['partner.card.rank.line'].create_partner_card_rank_detail(False, self, partner_card_rank.id, value_to_upper_order, new_rank.id, program.card_rank_id.id, total_value_to_up, program.id)
                            break
        else:
            for program in member_cards:
                if sale_id.order_partner_id.group_id.id == program.customer_group_id.id and \
                        (sale_id.order_partner_id.retail_type_ids and any(retail_type in program.partner_retail_ids for retail_type in sale_id.order_partner_id.retail_type_ids)):
                    value_to_upper_order = self.amount_residual - sale_id.x_voucher
                    if value_to_upper_order >= program.min_turnover:
                        self.env['partner.card.rank'].create_partner_card_rank(False, self, value_to_upper_order, program.id, program.card_rank_id.id)
                        break
