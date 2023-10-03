from odoo import fields, models, _, api


class StockTransfer(models.Model):
    _inherit = 'stock.transfer'

    defective_product_ids = fields.Many2many('product.defective')


class StockTransferLine(models.Model):
    _inherit = 'stock.transfer.line'

    defective_product_id = fields.Many2one('product.defective')
