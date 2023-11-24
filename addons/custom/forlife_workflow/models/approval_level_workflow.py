from odoo import api, fields, models


class ApprovalLevelWorkflow(models.Model):
    _name = 'approval.level.workflow'
    _description = 'Cấp phê duyệt'
    _order = 'name'

    name = fields.Integer('Cấp', default=lambda s: s.env['approval.level.workflow'].search([], order='name desc', limit=1).name + 1)

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'Cấp phê duyệt đã tồn tại, vui lòng chọn lại !'),
    ]

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, f'Cấp {record.name}'))
        return res
