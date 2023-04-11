from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # number_days_change_refund = fields.Integer('Number days change/refurd')

    @api.model
    def get_product_auto(self):
        product_id = self.search([('is_product_auto', '=', True)], limit=1)
        if product_id:
            return product_id.id
        return False