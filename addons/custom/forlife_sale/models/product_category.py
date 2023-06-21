from odoo import api, fields, models

class ProductCategory(models.Model):
    _inherit = 'product.category'

    x_property_account_return_id = fields.Many2one('account.account', string='Tài khoản trả hàng', company_dependent=True)
