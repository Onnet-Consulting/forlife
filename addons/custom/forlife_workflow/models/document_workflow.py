from odoo import api, fields, models


class DocumentWorkflow(models.Model):
    _name = 'document.workflow'
    _description = 'Luồng chứng từ chạy workflow'
    _order = 'code'
    _rec_name = 'code'

    code = fields.Char('Mã workflow', readonly=1, default='Mới')
    business_group_id = fields.Many2one('business.group.workflow', 'Mã nhóm nghiệp vụ', ondelete='restrict')

    # document type
    document_id = fields.Many2one('ir.model', 'Chứng từ')
    model_name = fields.Char(related='document_id.model')
    document_domain = fields.Char('Bộ lọc')
    from_date = fields.Date(string='Từ ngày')
    to_date = fields.Date(string='Đến ngày')
    active = fields.Boolean('Trạng thái hoạt động', default=True)
    allow_recall = fields.Boolean('Cho phép chạy lại', default=False)

    detail_ids = fields.One2many('document.detail.workflow', 'document_workflow_id', string='Chi tiết phê duyệt')
    authorization_ids = fields.One2many('authorization.workflow', 'document_workflow_id', string='Chi tiết ủy quyền')

    @api.onchange('document_id')
    def onchange_document_id(self):
        self.document_domain = None

    @api.model_create_multi
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        for line in vals_list:
            line['code'] = self.env['ir.sequence'].next_by_code('document.workflow')
        res = super(DocumentWorkflow, self).create(vals_list)
        self.clear_caches()
        return res


class DocumentDetailWorkflow(models.Model):
    _name = 'document.detail.workflow'
    _description = 'Chi tiết luồng chứng từ chạy workflow'
    _order = 'document_workflow_id, approval_level, value_from'
    _rec_name = 'document_workflow_id'

    document_workflow_id = fields.Many2one('document.workflow', 'Workflow', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    value_from = fields.Monetary('Giá trị từ', default=0, currency_field='currency_id')
    approval_level = fields.Many2one('approval.level.workflow', string='Cấp phê duyệt')
    approval_user_id = fields.Many2one('res.users', 'Người phê duyệt')
    request_user_id = fields.Many2one('res.users', 'Người yêu cầu')
    user_number_need_approval = fields.Integer('Số lượng user cần phê duyệt', default=1)
    status_approval_after = fields.Selection([('none', 'Trống'), ('yes', 'Duyệt'), ('no', 'Từ chối'), ('all', 'Tất cả trạng thái'), ], 'Trạng thái cấp phê duyệt trước đó', default='none')
    user_number_reject = fields.Integer('Số lượng user từ chối', default=1)
    type_action_user = fields.Selection([('d', 'Decision'), ('i', 'Information')], 'Loại hành động', default='d')
    from_date = fields.Date(string='Từ ngày')
    to_date = fields.Date(string='Đến ngày')


class AuthorizationWorkflow(models.Model):
    _name = 'authorization.workflow'
    _description = 'Luồng ủy quyền cho người dùng khác'
    _order = 'document_workflow_id, approval_level'
    _rec_name = 'document_workflow_id'

    document_workflow_id = fields.Many2one('document.workflow', 'Workflow', required=True)
    approval_level = fields.Many2one('approval.level.workflow', string='Cấp phê duyệt')
    approval_user_id = fields.Many2one('res.users', 'Người phê duyệt', required=1)
    authorization_user_id = fields.Many2one('res.users', 'Người được ủy quyền', required=1)
    from_date = fields.Date(string='Từ ngày')
    to_date = fields.Date(string='Đến ngày')
