from odoo import api, fields, models


class SetVourcher(models.Model):
    _name = 'setup.vourcher'
    _description = 'Set Vourcher code'

    purpose_vourcher = fields.Selection([('gift', 'Gift'), ('pay', 'Pay')], string='Mục đích sử dụng', required=True)

    applicable_object = fields.Char('Đối tượng', required=True)

    ref = fields.Char('Mã viết tắt', required=True)

    def name_get(self):
        return [(setup_vourcher.id, '%s %s' % (setup_vourcher.applicable_object, setup_vourcher.ref)) for setup_vourcher in self]

    _sql_constraints = [
        ('unique_ref', 'UNIQUE(ref)', 'Ref must be unique!')
    ]
