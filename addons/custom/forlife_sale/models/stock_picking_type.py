from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    x_is_return = fields.Boolean(string='Loại trả hàng')
