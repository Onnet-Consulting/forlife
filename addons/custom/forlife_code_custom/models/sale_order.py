from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model_create_multi
    def create(self, vals):
        result = super(SaleOrder, self).create(vals)
        sequence = 0
        for res in result:
            if not res.x_is_return:
                if res.x_sale_chanel == 'wholesale':
                    declare_code = '008' # DH ban buon
                elif res.x_sale_chanel == 'intercompany':
                    declare_code = '007' # DH lien cong ty
                else:
                    declare_code = '009' # DH online, pos
            else:
                declare_code = '012' #DH tra
                if res.source_record:
                    declare_code = '013' # DH tra tu Nhanh
            declare_code_id = self.env['declare.code']._get_declare_code(declare_code, self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code(res.company_id.id,'sale_order','name',sequence)
                sequence += 1
        return result

