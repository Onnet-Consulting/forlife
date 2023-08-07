import logging

from odoo import api, fields, models


class PosOlDiscountDetails(models.Model):
    _name = 'pos.order.line.discount.details'
    _description = 'POS discount details'

    name = fields.Char('Program Name', compute='_compute_name')
    pos_order_line_id = fields.Many2one('pos.order.line')

    type = fields.Selection([
        ('ctkm', 'CTKM'),
        ('point', 'Point'),
        ('make_price', 'Make Price'),
        ('card', 'Card'),
        ('product_defective', 'Product Defective'),
        ('handle', 'Handle'),
        ('change_refund', 'Change/Refund')
    ], string='Type')
    program_name = fields.Many2one('points.promotion', related='pos_order_line_id.order_id.program_store_point_id')
    listed_price = fields.Monetary('Listed price')
    recipe = fields.Float('Recipe')
    discounted_amount = fields.Monetary('Pro Discounted Amount', currency_field='currency_id')
    money_reduced = fields.Monetary('Money Reduced', compute='_compute_money_reduced', store=True)  # compute_field
    currency_id = fields.Many2one('res.currency', related='pos_order_line_id.currency_id')

    @api.depends('recipe', 'type', 'discounted_amount')
    def _compute_money_reduced(self):
        for rec in self:
            if rec.type == 'point':
                rec.money_reduced = rec.recipe * 1000
            elif rec.type == 'ctkm':
                rec.money_reduced = rec.discounted_amount
            else:
                rec.money_reduced = rec.recipe

    def get_money_reduced(self):
        if self.type == 'point':
            return self.recipe * 1000
        return self.recipe

    def _compute_name(self):
        for line in self:
            line.name = line.get_name()

    def get_name(self):
        name = '/'
        if self.type == 'point':
            name = self.program_name.name
        return name

    def _export_for_ui(self):
        return {
            'id': self.id,
            'pos_order_line_id': self.pos_order_line_id.id,
            'money_reduced': self.money_reduced,
            'type': self.type,
        }
