from odoo import api, fields, models


class GenerateCodeBySequence(models.AbstractModel):
    _name = 'generate.code.by.sequence'
    _description = 'Tự động sinh mã'

    code = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        for line in vals_list:
            line['code'] = self.env['ir.sequence'].next_by_code(self._name)
        return super().create(vals_list)


class BusinessGroupWorkflow(models.Model):
    _name = 'business.group.workflow'
    _inherit = 'generate.code.by.sequence'
    _description = 'Nhóm nghiệp vụ chạy workflow'
    _order = 'name'

    name = fields.Char('Tên mô tả', required=1)
    code = fields.Char('Mã nhóm nghiệp vụ', readonly=1, default='Mới')
    declare_category_id = fields.Many2one('declare.category', 'Mã nhóm chứng từ', ondelete='restrict')
