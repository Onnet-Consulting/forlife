from odoo import api, fields, models


class ResBank(models.Model):
    _inherit = 'res.bank'

    transaction_name = fields.Char('Tên giao dịch')
    headbank_id = fields.Many2one('res.headbank', string='Ngân hàng mẹ')
    level = fields.Many2one('bank.level', string='Cấp độ')
    license_start = fields.Char('Giấy phép thành lập')
    date_valid = fields.Date('Ngày hiệu lực')

class ResParterBank(models.Model):
    _inherit = 'res.partner.bank'

    gl_account = fields.Many2one('account.account', string='GLAccount')
    description = fields.Text('Description')
