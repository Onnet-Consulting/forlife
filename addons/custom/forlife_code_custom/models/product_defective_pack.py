from odoo import api, fields, models, _


class ProductDefectivePack(models.Model):
    _inherit = 'product.defective.pack'

    @api.model_create_multi
    def create(self, vals):
        result = super(ProductDefectivePack, self).create(vals)
        sequence = 0
        for res in result:
            location_code = res.store_id.warehouse_id.code or ''
            location_des_code = res.store_id.warehouse_id.code or ''
            declare_code_id = self.env['declare.code']._get_declare_code('027', self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code(res.company_id.id,'product.defective.pack','name',sequence,location_code,location_des_code)
                sequence += 1
        return result
    
class ProductDefective(models.Model):
    _inherit = 'product.defective'

    name = fields.Char(string='Name',related='pack_id.name')

