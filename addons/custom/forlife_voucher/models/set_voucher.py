from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SetVoucher(models.Model):
    _name = 'setup.voucher'
    _description = 'Set Voucher code'

    purpose_voucher = fields.Selection([('gift', 'Gift'), ('pay', 'Pay')], string='Mục đích sử dụng', required=True)

    applicable_object = fields.Char('Đối tượng', required=True)

    ref = fields.Char('Mã viết tắt', required=True)

    def name_get(self):
        return [(setup_voucher.id, '%s %s' % (setup_voucher.applicable_object, setup_voucher.ref)) for setup_voucher in self]

    _sql_constraints = [
        ('unique_ref', 'UNIQUE(ref)', 'Ref must be unique!')
    ]

    def unlink(self):
        for rec in self:
            program_used = self.env['program.voucher'].search([('purpose_id', '=', rec.id)])
            if program_used:
                raise ValidationError(_('Không thể hoàn thành thao tác: Bản ghi "{}" yêu cầu bản ghi bị xóa. Nếu có thể, hãy lưu trữ nó để thay thế.'.format(program_used.name)))
