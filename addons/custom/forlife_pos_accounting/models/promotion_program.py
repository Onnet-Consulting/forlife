from odoo import fields, models


class InheritPromotionProgram(models.Model):
    _inherit = 'promotion.program'

    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', index=True)
    product_discount_id = fields.Many2one(
        comodel_name='product.product', string='Discount Product', index=True,
        domain="[('is_promotion', '=', True)]"
    )
