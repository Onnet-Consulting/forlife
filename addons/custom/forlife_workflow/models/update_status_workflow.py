from odoo import api, fields, models


class UpdateStatusWorkflow(models.Model):
    _name = 'update.status.workflow'
    _description = 'Ghi nhận cập nhật trạng thái tại các bước chạy workflow'

    document_code = fields.Char('Mã chứng từ chi tiết')
    approval_level = fields.Many2one('approval.level.workflow', string='Cấp phê duyệt', ondelete='restrict')
    user_id = fields.Many2one('res.users', 'Người thực hiện')
    result = fields.Char('Kết quả')
    round = fields.Integer('Vòng chạy workflow', default=1)
