from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_price_account_id = fields.Many2one('account.account', 'Account Price', company_dependent=True,
                                                domain="[('company_id', '=', allowed_company_ids[0])]",
                                                check_company=True)
