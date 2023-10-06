from odoo import api, fields, models, _


class SplitProduct(models.Model):
    _inherit = 'split.product'

    company_id = fields.Many2one('res.company', string="Công ty", default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals):
        result = super(SplitProduct, self).create(vals)
        sequence = 0
        for res in result:
            declare_code_id = self.env['declare.code']._get_declare_code('021', res.company_id.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code(res.company_id.id,'split.product','name',sequence)
                sequence += 1
        return result

