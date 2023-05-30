from odoo import fields, models, api, _
ACCOUNT_DOMAIN = "['&', '&', '&', ('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card')), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"


# class InheritProductCategory(models.Model):
#     _inherit = 'product.category'
#
#     property_account_promotion_expense_categ_id = fields.Many2one(
#         comodel_name='account.account',
#         string='Promotion Expense Account',
#         domain=ACCOUNT_DOMAIN,
#         company_dependent=True,
#         index=True
#     )


class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    property_account_promotion_expense_id = fields.Many2one(
        comodel_name='account.account',
        string='Promotion Expense Account',
        domain=ACCOUNT_DOMAIN,
        company_dependent=True,
        index=True
    )

    is_promotion = fields.Boolean(string='Is Promotion', index=True)

    def get_product_promotion_expense_account(self):
        self.ensure_one()
        return self.property_account_promotion_expense_id

    def check_is_promotion(self):
        self.ensure_one()
        return self.is_promotion


class InheritProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_promotion_expense_account(self):
        return self.product_tmpl_id.get_product_promotion_expense_account()

    def check_is_promotion(self):
        return self.product_tmpl_id.check_is_promotion()
