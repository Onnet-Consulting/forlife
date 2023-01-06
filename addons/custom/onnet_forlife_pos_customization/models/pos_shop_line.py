from odoo import api, fields, models


class PosShopLine(models.Model):
    _name = 'pos.shop.line'

    pos_config_id = fields.Many2one('pos.config')
    pos_shop_id = fields.Many2one('pos.shop')
