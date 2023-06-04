from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    import_or_export = fields.Selection(
        [('other_import', 'Nhập khác'),
         ('other_export', 'Xuất khác')],
        string='Nhập/xuất khác')
