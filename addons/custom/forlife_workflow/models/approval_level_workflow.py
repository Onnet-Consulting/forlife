from odoo import api, fields, models


class ApprovalLevelWorkflow(models.Model):
    _name = 'approval.level.workflow'
    _description = 'Cấp phê duyệt'
    _order = 'name'

    name = fields.Integer('Cấp', default=1)

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'Cấp phê duyệt đã tồn tại, vui lòng chọn lại !'),
    ]

    def get_approval_level(self):
        return [(r.name, r.name) for r in self.env['approval.level.workflow'].search([])]
