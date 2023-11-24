from odoo import api, fields, models


class AuthorizationWorkflow(models.Model):
    _name = 'authorization.workflow'
    _inherit = 'generate.code.by.sequence'
    _description = 'Luồng ủy quyền cho người dùng khác'
    _rec_name = 'code'

    code = fields.Char('Mã ủy quyền', readonly=1, default='Mới')
    type_action_user = fields.Selection([('wf', 'Theo workflow'), ('dd', 'Theo chi tiết chứng từ')], 'Hình thức ủy quyền', default='wf', required=1)
    document_workflow_id = fields.Many2one('document.workflow', 'Workflow')
    document_code = fields.Char('Mã chứng từ chi tiết')
    approval_level = fields.Many2one('approval.level.workflow', string='Cấp phê duyệt', required=1, ondelete='restrict')
    approval_user_id = fields.Many2one('res.users', 'Người phê duyệt', required=1)
    authorization_user_id = fields.Many2one('res.users', 'Người được ủy quyền', required=1)
    from_date = fields.Date(string='Ủy quyền từ ngày')
    to_date = fields.Date(string='Ủy quyền đến ngày')
