from odoo import api, fields, models


class ResHeadBank(models.Model):
    _name = 'res.headbank'
    _description = 'Master Bank'

    bank_code = fields.Char('Mã ngân hàng', required=True)
    name = fields.Char('Tên ngân hàng')

    _sql_constraints = [
        ('unique_bank_code', 'UNIQUE(bank_code)', 'Code Bank must be unique!')
    ]


class BankLevel(models.Model):
    _name = 'bank.level'

    _description = 'Bank Level'

    code = fields.Char('Code')
    level = fields.Char('Cấp độ')

    def name_get(self):
        return [(rec.id, '%s' % rec.level) for rec in self]

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]