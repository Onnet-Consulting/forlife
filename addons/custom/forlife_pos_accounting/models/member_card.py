from odoo import fields, models


class InheritMemberCard(models.Model):
    _inherit = 'member.card'

    product_discount_id = fields.Many2one(
        comodel_name='product.product', string='Discount Product', index=True, required=True,
        domain="[('is_promotion', '=', True)]"
    )
