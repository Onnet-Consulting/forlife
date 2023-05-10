from odoo import api, fields, models, _

class ProductCategory(models.Model):
    _inherit = 'product.category'

    number_days_change_refund = fields.Integer('Hạn đổi trả', tracking=True)

    @api.model
    def create(self, vals_list):
        if 'number_days_change_refund' in vals_list:
            products = self.env['product.template'].search([('categ_id','=', self.id)])
            for record in products:
                record.number_days_change_refund = int(vals_list['number_days_change_refund'])
        return super(ProductCategory, self).create(vals_list)

    def write(self, vals):
        if 'number_days_change_refund' in vals:
            products = self.env['product.template'].search([('categ_id','=', self.id)])
            for record in products:
                record.number_days_change_refund = int(vals['number_days_change_refund'])
        return super(ProductCategory, self).write(vals)