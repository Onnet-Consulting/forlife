from odoo import fields, models, api, _


class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    is_promotion = fields.Boolean(string='Is Promotion', index=True)

    def get_product_gift_account(self):
        self.ensure_one()
        return self.categ_id.product_gift_account_id

    def check_is_promotion(self):
        self.ensure_one()
        return self.is_promotion or False


class InheritProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_gift_account(self):
        return self.product_tmpl_id.get_product_gift_account()

    def check_is_promotion(self):
        return self.product_tmpl_id.check_is_promotion()
