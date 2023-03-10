from odoo import api, fields, models


class PosOlDiscountDetails(models.Model):
    _inherit = 'pos.order.line.discount.details'

    card_rank_program_id = fields.Many2one('member.card', related='pos_order_line_id.order_id.card_rank_program_id')

    def get_money_reduced(self):
        if self.type == 'card':
            return - (self.recipe * self.listed_price / 100) * self.pos_order_line_id.qty
        return super().get_money_reduced()

    def get_name(self):
        if self.card_rank_program_id:
            return self.card_rank_program_id.name
        return super().get_name()
    