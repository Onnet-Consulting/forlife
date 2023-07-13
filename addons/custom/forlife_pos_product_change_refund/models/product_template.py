from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    number_days_change_refund = fields.Integer('Number days change/refurd', tracking=True)
    is_product_auto = fields.Boolean('Product Auto', default=False, copy=False)
    is_voucher_auto = fields.Boolean('Voucher Auto', default=False, copy=False)

    @api.constrains('is_product_auto')
    def check_product_auto(self):
        for item in self:
            if item.is_product_auto:
                product_id = self.search([('is_product_auto', '=', True), ('id', '!=', item.id)])
                if product_id:
                    raise ValidationError(_("Product with information 'Product Auto' unique."))



