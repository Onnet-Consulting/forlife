from odoo import api, fields, models, _


class SplitProduct(models.Model):
    _inherit = 'split_product'

    @api.model_create_multi
    def create(self, vals):
        result = super(SplitProduct, self).create(vals)
        for res in result:
            declare_code_id = self.env['declare.code']._get_declare_code('021', self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code('split_product','name')
        return result

