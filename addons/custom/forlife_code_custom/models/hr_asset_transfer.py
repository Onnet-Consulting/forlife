from odoo import api, fields, models, _


class HRAssetTransfer(models.Model):
    _inherit = 'hr.asset.transfer'

    @api.model_create_multi
    def create(self, vals):
        result = super(HRAssetTransfer, self).create(vals)
        sequence = 0
        for res in result:
            declare_code_id = self.env['declare.code']._get_declare_code('025', res.company_id.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code(res.company_id.id,'hr.asset.transfer','name',sequence)
                sequence += 1
        return result

