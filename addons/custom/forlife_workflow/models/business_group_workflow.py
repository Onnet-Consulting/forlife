from odoo import api, fields, models


class BusinessGroupWorkflow(models.Model):
    _name = 'business.group.workflow'
    _description = 'Nhóm nghiệp vụ chạy workflow'
    _order = 'name'

    name = fields.Char('Tên mô tả', required=1)
    code = fields.Char('Mã nhóm nghiệp vụ', readonly=1, default='Mới')
    declare_category_id = fields.Many2one('declare.category', 'Mã nhóm chứng từ', ondelete='restrict')

    @api.model_create_multi
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        for line in vals_list:
            line['code'] = self.env['ir.sequence'].next_by_code('business.group.workflow')
        res = super(BusinessGroupWorkflow, self).create(vals_list)
        self.clear_caches()
        return res
