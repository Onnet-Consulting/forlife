from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    price_account_id = fields.Many2one('account.account', 'Account Price')
