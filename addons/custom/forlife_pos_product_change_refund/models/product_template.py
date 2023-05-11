from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    number_days_change_refund = fields.Integer('Number days change/refurd', tracking=True)
    is_product_auto = fields.Boolean('Product Auto', default=False, copy=False)
    is_voucher_auto = fields.Boolean('Voucher Auto', default=False, copy=False)

    @api.model
    def create(self, vals_list):
        if 'categ_id' in vals_list:
            categ = self.env['product.category'].search([('id','=', int(vals_list['categ_id']))])
            vals_list['number_days_change_refund'] = categ.number_days_change_refund
        return super(ProductTemplate, self).create(vals_list)

    def write(self, vals_list):
        if 'categ_id' in vals_list:
            categ = self.env['product.category'].search([('id','=', int(vals_list['categ_id']))])
            vals_list['number_days_change_refund'] = categ.number_days_change_refund
        return super(ProductTemplate, self).write(vals_list)

    @api.constrains('is_product_auto')
    def check_product_auto(self):
        for item in self:
            if item.is_product_auto:
                product_id = self.search([('is_product_auto', '=', True), ('id', '!=', item.id)])
                if product_id:
                    raise ValidationError(_("Product with information 'Product Auto' unique."))

    @api.constrains('is_voucher_auto')
    def check_voucher_auto(self):
        for item in self:
            if item.is_voucher_auto:
                product_id = self.search([('is_voucher_auto', '=', True), ('id', '!=', item.id)])
                if product_id:
                    raise ValidationError(_("Product with information 'Voucher Auto' unique."))


