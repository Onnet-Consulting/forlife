from odoo import api, fields, models


class PosOlDiscountDetails(models.Model):
    _name = 'pos.order.line.discount.details'

    pos_order_line_id = fields.Many2one('pos.order.line')
    type = fields.Selection([('ctkm', 'CTKM'), ('point', 'Point'), ('make_price', 'Make Price'), ('card', 'Card')], string='Type')
    program_name = fields.Many2one('points.promotion', related='pos_order_line_id.order_id.program_store_point_id')
    listed_price = fields.Monetary('Listed price')
    recipe = fields.Float('Recipe')
    money_reduced = fields.Monetary('Money Reduced', compute='_compute_money_reduced')  # compute_field
    currency_id = fields.Many2one('res.currency', related='pos_order_line_id.currency_id')

    @api.depends('recipe')
    def _compute_money_reduced(self):
        for rec in self:
            if rec.type == 'card':
                rec.money_reduced = rec.recipe * rec.listed_price / 100
            else:
                rec.money_reduced = -rec.recipe * 1000
