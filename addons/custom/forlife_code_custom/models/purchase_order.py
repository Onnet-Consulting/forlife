from odoo import api, fields, models, _

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model_create_multi
    def create(self, vals):
        result = super(PurchaseOrder, self).create(vals)
        sequence = 0
        for res in result:
            if not res.is_return:
                if not res.is_inter_company:
                    if res.purchase_type == 'product': #DMH hang hoa
                        declare_code = '002'
                    elif res.purchase_type == 'asset': #DMH tai san
                        declare_code = '003'
                    elif res.purchase_type == 'service': #DMH dich vu
                        declare_code = '004'
                else:
                    declare_code = '005' #DMH lien cong ty
            else:
                declare_code = '010' #Don tra hang ncc
            declare_code_id = self.env['declare.code']._get_declare_code(declare_code, self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code(res.company_id.id,'purchase.order','name',sequence)
                sequence += 1
        return result

