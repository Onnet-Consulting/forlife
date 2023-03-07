from odoo import api, fields, models


class PosOlDiscountDetails(models.Model):
    _inherit = 'pos.order.line.discount.details'

    card_rank_program_id = fields.Many2one('member.card', related='pos_order_line_id.order_id.card_rank_program_id')
