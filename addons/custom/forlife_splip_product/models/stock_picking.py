from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    split_product_id = fields.Many2one('split.product')