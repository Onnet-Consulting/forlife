from odoo import api, fields, models, _


class ProductDefective(models.Model):
    _inherit = 'product.defective'

    name = fields.Char(default='New')

    @api.model_create_multi
    def create(self, vals):
        result = super(ProductDefective, self).create(vals)
        for res in result:
            location_code = res.store_id.warehouse_id.code or ''
            location_des_code = res.store_id.warehouse_id.code or ''
            declare_code_id = self.env['declare.code']._get_declare_code('027', self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code('product_defective','name',location_code,location_des_code)
        return result

