from odoo import api, fields, models


class PosOlDiscountDetails(models.Model):
    _inherit = 'pos.order.line.discount.details'

    # discounted_amount = fields.Monetary('Pro Discounted Amount', currency_field='currency_id')

    def get_money_reduced(self):
        if self.type == 'ctkm':
            return self.discounted_amount
        return super().get_money_reduced()
