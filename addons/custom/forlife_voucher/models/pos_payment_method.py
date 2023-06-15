from odoo import api, fields, models

class PaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    account_other_income = fields.Many2one('account.account', 'Account Other Income')
    account_general = fields.Many2one('account.account', 'Account General')
    account_other_fee = fields.Many2one('account.account',' Tài khoản chi phí khác')
