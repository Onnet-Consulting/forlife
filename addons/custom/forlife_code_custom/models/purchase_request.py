from odoo import api, fields, models, _

class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    @api.model_create_multi
    def create(self, vals):
        result = super(PurchaseRequest, self).create(vals)
        for res in result:
            declare_code_id = self.env['declare.code']._get_declare_code('001', self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code('purchase_request','name')
        return result

