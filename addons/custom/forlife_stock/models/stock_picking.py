from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transfer_id = fields.Many2one('stock.transfer')
