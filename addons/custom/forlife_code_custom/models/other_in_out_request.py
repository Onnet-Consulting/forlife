from odoo import api, fields, models, _

class ForlifeOtherInOutRequest(models.Model):
    _inherit = "forlife.other.in.out.request"

    @api.model_create_multi
    def create(self, vals):
        result = super(ForlifeOtherInOutRequest, self).create(vals)
        sequence = 0
        for res in result:
            if res.type_other == 'other_import':
                declare_code = '014' # YC Nhap khac
            else:
                declare_code = '016' # YC Xuat khac
            declare_code_id = self.env['declare.code']._get_declare_code(declare_code, self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code(res.company_id.id,'forlife_other_in_out_request','name',sequence)
                sequence += 1
        return result

