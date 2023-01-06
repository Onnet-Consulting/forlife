from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_shop_id = fields.Many2one('pos.shop')