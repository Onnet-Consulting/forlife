from odoo import api, fields, models, _

class ProductCategory(models.Model):
    _inherit = 'product.category'

    number_days_change_refund = fields.Integer('Hạn đổi trả')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductCategory, self).create(vals_list)
        if 'number_days_change_refund' in vals_list:
            products = self.env['product.template'].search([('categ_id','=', res.id)])
            if products:
                product_ids = []
                for record in products:
                    product_ids.append(record.id)
                product_ids = tuple(product_ids) if len(product_ids) > 1 else f"({product_ids[0]})"
                sql = f"update product_template set number_days_change_refund = {vals_list['number_days_change_refund']} where id in {product_ids}"
                self._cr.execute(sql)
        return res

    def write(self, vals):
        if 'number_days_change_refund' in vals:
            products = self.env['product.template'].search([('categ_id','=', self.id)])
            if products:
                product_ids = []
                for record in products:
                    product_ids.append(record.id)
                product_ids = tuple(product_ids) if len(product_ids) > 1 else f"({product_ids[0]})"
                sql = f"UPDATE product_template SET number_days_change_refund = {vals['number_days_change_refund']} WHERE id IN {product_ids}"
                self._cr.execute(sql)
            child_categorys = self.search([('parent_id','=',self.id)])
            if child_categorys:
                for child in child_categorys:
                    child.number_days_change_refund = vals['number_days_change_refund']
        return super(ProductCategory, self).write(vals)