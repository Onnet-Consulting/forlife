from odoo import api, fields, models


class PosShop(models.Model):
    _name = 'pos.shop'

    name = fields.Char('Name')
    pos_shop_line_ids = fields.One2many('pos.shop.line', 'pos_shop_id', 'Pos')

    account_intermediary_pos = fields.Many2one('account.account', "Account intermediary")