from odoo import api, fields, models


class PosOlDiscountDetails(models.Model):
    _inherit = 'pos.order.line.discount.details'

    def get_money_reduced(self):
        if self.type == 'card':
            return self.recipe
        return super().get_money_reduced()

    def get_name(self):
        if self.type == 'card':
            return self.pos_order_line_id.order_id.card_rank_program_id.name
        return super().get_name()
    