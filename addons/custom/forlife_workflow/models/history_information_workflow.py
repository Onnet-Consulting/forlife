from odoo import api, fields, models


class HistoryInformationWorkflow(models.Model):
    _name = 'history.information.workflow'
    _description = 'Thông tin kết quả user feedback'

    document_code = fields.Char('Mã chứng từ chi tiết')
    approval_level = fields.Many2one('approval.level.workflow', string='Cấp phê duyệt', ondelete='restrict')
    user_id = fields.Many2one('res.users', 'Người thực hiện')
    result = fields.Char('Kết quả')
    content = fields.Char('Nội dung')
    request_date = fields.Date('Ngày yêu cầu')
    implementation_date = fields.Date('Ngày thực hiện')
