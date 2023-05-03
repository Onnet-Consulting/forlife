# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_rank = fields.Boolean('Is Rank', default=False)
    card_rank_program_id = fields.Many2one('member.card', 'Card Rank Program', ondelete='restrict')

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        self.update_partner_card_rank()
        if self.card_rank_program_id:
            total_amount_discount = abs(sum(self.mapped('lines.discount_details_lines').filtered(lambda f: f.type == 'card').mapped('money_reduced')))
            self.accounting_card_rank_discount(total_amount_discount) if total_amount_discount else None
        return res

    def update_partner_card_rank(self):
        member_cards = self.env['member.card'].get_member_card_by_date(self.date_order, self.config_id.store_id.brand_id.id)
        if not member_cards:
            return False
        is_rank = False
        partner_card_rank = self.partner_id.card_rank_ids.filtered(lambda f: f.brand_id == self.config_id.store_id.brand_id)
        if partner_card_rank:
            new_rank = partner_card_rank.card_rank_id
            for program in member_cards:
                if self.partner_id.group_id.id == program.customer_group_id.id and \
                        (self.partner_id.retail_type_ids and any(retail_type in program.partner_retail_ids for retail_type in self.partner_id.retail_type_ids)):
                    is_rank = True
                    value_to_upper_order = sum([payment_method.amount for payment_method in self.payment_ids if payment_method.payment_method_id.id in program.payment_method_ids.ids])
                    total_value_to_up = value_to_upper_order + sum(partner_card_rank.line_ids.filtered(lambda f: f.order_date >= (self.date_order - timedelta(days=program.time_set_rank))).mapped('value_to_upper'))
                    if new_rank.priority >= program.card_rank_id.priority:
                        self.create_partner_card_rank_detail(partner_card_rank.id, value_to_upper_order, new_rank.id, new_rank.id, total_value_to_up, program.id)
                        self.save_order_to_program(program)
                        break
                    else:
                        if total_value_to_up >= program.min_turnover:
                            self.create_partner_card_rank_detail(partner_card_rank.id, value_to_upper_order, new_rank.id, program.card_rank_id.id, total_value_to_up, program.id)
                            self.save_order_to_program(program)
                            break
        else:
            for program in member_cards:
                if self.partner_id.group_id.id == program.customer_group_id.id and \
                        (self.partner_id.retail_type_ids and any(retail_type in program.partner_retail_ids for retail_type in self.partner_id.retail_type_ids)):
                    is_rank = True
                    value_to_upper_order = sum([payment_method.amount for payment_method in self.payment_ids if payment_method.payment_method_id.id in program.payment_method_ids.ids])
                    if value_to_upper_order >= program.min_turnover:
                        self.create_partner_card_rank(value_to_upper_order, program.id, program.card_rank_id.id)
                        self.save_order_to_program(program)
                        break
        if is_rank:
            self.sudo().write({'is_rank': True})

    def create_partner_card_rank(self, value_to_upper_order, program_id, rank_id):
        res = self.env['partner.card.rank'].sudo().create({
            'customer_id': self.partner_id.id,
            'brand_id': self.config_id.store_id.brand_id.id,
            'line_ids': [(0, 0, {
                'order_id': self.id,
                'order_date': self.date_order,
                'real_date': self.create_date,
                'value_orders': self.amount_total,
                'value_to_upper': value_to_upper_order,
                'old_card_rank_id': rank_id,
                'new_card_rank_id': rank_id,
                'value_up_rank': 0,
                'program_cr_id': program_id,
            })]
        })
        return res

    def create_partner_card_rank_detail(self, partner_card_rank_id, value_to_upper, old_rank_id, new_rank_id, total_value_to_up, program_id):
        self.env['partner.card.rank.line'].sudo().create({
            'partner_card_rank_id': partner_card_rank_id,
            'order_id': self.id,
            'order_date': self.date_order,
            'real_date': self.create_date,
            'value_orders': self.amount_total,
            'value_to_upper': value_to_upper,
            'old_card_rank_id': old_rank_id,
            'new_card_rank_id': new_rank_id,
            'value_up_rank': total_value_to_up if old_rank_id != new_rank_id else 0,
            'program_cr_id': program_id,
        })

    def save_order_to_program(self, program):
        program.sudo().write({
            'order_ids': [(4, self.id)]
        })

    @api.model
    def _order_fields(self, ui_order):
        res = super()._order_fields(ui_order)
        if 'card_rank_program_id' not in res and ui_order.get('card_rank_program'):
            res.update({'card_rank_program_id': ui_order.get('card_rank_program')})
        return res

    def accounting_card_rank_discount(self, total_amount_discount):
        values = self._prepare_cr_discount_account_move()
        values['line_ids'] = self._prepare_cr_discount_account_move_line(total_amount_discount)
        res = self.env['account.move'].sudo().create(values)
        return res.action_post() if res else False

    def _prepare_cr_discount_account_move(self):
        return {
            'pos_order_id': self.id,
            'ref': self.name,
            'date': self.date_order,
            'journal_id': self.card_rank_program_id.journal_id.id,
        }

    def _prepare_cr_discount_account_move_line(self, total_amount_discount):
        if self.card_rank_program_id.is_register and self.card_rank_program_id.register_from_date <= self.date_order.date() and self.card_rank_program_id.register_to_date >= self.date_order.date():
            debit_account = self.card_rank_program_id.discount_account_id.id
        else:
            debit_account = self.card_rank_program_id.value_account_id.id
        return [
            (0, 0, {
                'account_id': debit_account,
                'debit': total_amount_discount,
                'analytic_account_id': self.config_id.store_id.analytic_account_id.id,
            }),
            (0, 0, {
                'account_id': self.partner_id.property_account_receivable_id.id,
                'credit': total_amount_discount,
                'partner_id': self.config_id.store_id.contact_id.id,
            }),
        ]


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    card_rank_applied = fields.Boolean('Card Rank Applied', default=False)
    card_rank_discount = fields.Float('Card Rank Discount', default=0)

    @api.model_create_multi
    def create(self, vals_list):
        for idx, line in enumerate(vals_list):
            if line.get('card_rank_discount') and line.get('card_rank_applied'):
                vals_list[idx]['discount_details_lines'] = line.get('discount_details_lines', []) + [
                    (0, 0, {
                        'type': 'card',
                        'listed_price': line['price_unit'],
                        'recipe': - line['card_rank_discount'],
                    })
                ]
        return super(PosOrderLine, self).create(vals_list)
