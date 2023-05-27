from odoo import api, fields, models, _

class StockLocation(models.Model):
    _inherit = 'stock.location'

    account_stock_give = fields.Many2one('account.account', 'Tài khoản kho kí gửi')