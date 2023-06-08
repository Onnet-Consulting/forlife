from odoo import fields, models
from datetime import date


class InheritPointsPromotion(models.Model):
    _inherit = 'points.promotion'

    product_discount_id = fields.Many2one(
        comodel_name='product.product', string='Discount Product', index=True, required=True,
        domain="[('is_promotion', '=', True)]"
    )
    is_state_registration = fields.Boolean(string='State Registration', index=True)
    state_registration_start = fields.Date(string='State Registration Start', index=True)
    state_registration_end = fields.Date(string='State Registration End', index=True)

    def check_validity_state_registration(self):
        self.ensure_one()
        return self.is_state_registration and self.state_registration_start <= date.today() <= self.state_registration_end
