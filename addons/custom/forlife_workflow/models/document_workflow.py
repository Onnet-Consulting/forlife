from odoo import api, fields, models


class DocumentWorkflow(models.Model):
    _name = 'document.workflow'
    _inherit = 'generate.code.by.sequence'
    _description = 'Luồng chứng từ chạy workflow'
    _order = 'code'
    _rec_name = 'code'

    code = fields.Char('Mã workflow', readonly=1, default='Mới')
    type_workflow = fields.Selection([('bg', 'Theo mã nhóm nghiệp vụ'), ('d', 'Theo kiểu chứng từ tùy chỉnh')], 'Loại chứng từ', default='bg', required=1)
    business_group_id = fields.Many2one('business.group.workflow', 'Mã nhóm nghiệp vụ', ondelete='restrict')
    document_id = fields.Many2one('ir.model', 'Chứng từ')
    model_name = fields.Char(related='document_id.model')
    document_domain = fields.Char('Bộ lọc chứng từ')
    from_date = fields.Date(string='Hiệu lực từ ngày')
    to_date = fields.Date(string='Hiệu lực đến ngày')
    active = fields.Boolean('Trạng thái hoạt động', default=True)
    allow_recall = fields.Boolean('Cho phép chạy lại', default=False)

    detail_ids = fields.One2many('document.detail.workflow', 'document_workflow_id', string='Chi tiết phê duyệt')

    @api.onchange('document_id')
    def onchange_document_id(self):
        self.document_domain = None


class DocumentDetailWorkflow(models.Model):
    _name = 'document.detail.workflow'
    _description = 'Chi tiết luồng chứng từ chạy workflow'
    _order = 'document_workflow_id, approval_level, value_from'
    _rec_name = 'document_workflow_id'

    document_workflow_id = fields.Many2one('document.workflow', 'Workflow', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    value_from = fields.Monetary('Giá trị từ', default=0, currency_field='currency_id')
    approval_level = fields.Many2one('approval.level.workflow', string='Cấp phê duyệt', ondelete='restrict')
    approval_user_id = fields.Many2one('res.users', 'Người phê duyệt')
    request_user_id = fields.Many2one('res.users', 'Người yêu cầu')
    user_number_need_approval = fields.Integer('Số lượng user cần phê duyệt', default=1)
    status_approval_after = fields.Selection([('none', 'Trống'), ('yes', 'Duyệt'), ('no', 'Từ chối'), ('all', 'Duyệt hoặc từ chối')], 'Trạng thái cấp phê duyệt trước đó', default='none', required=1)
    user_number_reject = fields.Integer('Số lượng user từ chối', default=1)
    type_action_user = fields.Selection([('d', 'Thực hiện phê duyệt'), ('i', 'Nhận thông tin')], 'Loại hành động', default='d', required=1)
    from_date = fields.Date(string='Áp dụng từ ngày')
    to_date = fields.Date(string='Áp dụng đến ngày')
