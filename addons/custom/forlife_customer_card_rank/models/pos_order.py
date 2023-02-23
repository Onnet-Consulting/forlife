# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_rank = fields.Boolean('Is Rank', default=False)

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        self.with_delay().update_partner_card_rank()
        return res

    def update_partner_card_rank(self):
        partner_card_rank = self.partner_id.card_rank_ids.filtered(lambda f: f.brand_id == self.config_id.store_id.brand_id)
        if partner_card_rank:
            self.validate_order_for_card_rank(partner_card_rank)
        else:
            partner_card_rank = self.create_partner_card_rank()
            self.validate_order_for_card_rank(partner_card_rank)

    def create_partner_card_rank(self):
        res = self.env['partner.card.rank'].sudo().create({
            'customer_id': self.partner_id.id,
            'brand_id': self.config_id.store_id.brand_id.id,
        })
        return res

    def validate_order_for_card_rank(self, partner_card_rank):
        member_cards = self.env['member.card'].get_member_card_by_date(self.date_order, partner_card_rank.brand_id.id)
        if not member_cards:
            return False
        new_rank = partner_card_rank.card_rank_id
        is_rank = False
        for program in member_cards:
            if partner_card_rank.customer_id.group_id.id in program.customer_group_ids.ids and (program.is_all_store or self.config_id.store_id.id in program.store_ids.ids):
                is_rank = True
                value_to_upper_order = sum([payment_method.amount for payment_method in self.payment_ids if payment_method.payment_method_id.id in program.payment_method_ids.ids])
                total_value_to_up = value_to_upper_order + sum(partner_card_rank.line_ids.filtered(lambda f: f.order_id and f.order_date >= (self.date_order - timedelta(days=program.time_set_rank))).mapped('value_to_upper'))
                if new_rank.priority >= program.card_rank_id.priority:
                    self.create_partner_card_rank_detail(partner_card_rank.id, value_to_upper_order, new_rank.id, new_rank.id)
                    partner_card_rank.sudo().write({'accumulated_sales': total_value_to_up})
                    self.save_order_to_program(program)
                    break
                else:
                    if total_value_to_up >= program.min_turnover:
                        self.create_partner_card_rank_detail(partner_card_rank.id, value_to_upper_order, new_rank.id, program.card_rank_id.id)
                        partner_card_rank.sudo().write({'accumulated_sales': total_value_to_up})
                        self.save_order_to_program(program)
                        break
        if is_rank:
            self.sudo().write({'is_rank': True})

    def create_partner_card_rank_detail(self, partner_card_rank_id, value_to_upper, old_rank_id, new_rank_id):
        self.env['partner.card.rank.line'].sudo().create({
            'partner_card_rank_id': partner_card_rank_id,
            'order_id': self.id,
            'order_date': self.date_order,
            'real_date': self.create_date,
            'value_orders': self.amount_total,
            'value_to_upper': value_to_upper,
            'old_card_rank_id': old_rank_id,
            'new_card_rank_id': new_rank_id,
        })

    def save_order_to_program(self, program):
        program.sudo().write({
            'order_ids': [(4, self.id)]
        })
