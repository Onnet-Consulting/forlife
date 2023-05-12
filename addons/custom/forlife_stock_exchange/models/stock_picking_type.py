from odoo import models, fields, api


class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    exchange_code = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing')
    ], string='Exchange Code', index=True)
