from odoo import models, fields, api


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    bom_model = fields.Char(string='BOM Model')
    bom_id = fields.Many2oneReference(string='BOM ID', model_field='bom_model')

    @api.onchange('amount_total', 'product_uom_qty', 'price_unit')
    def _onchange_amount(self):
        if not self.picking_id.exchange_code:
            return
        if self.is_amount_total:
            self.price_unit = self.amount_total / self.product_uom_qty
        else:
            self.amount_total = self.price_unit * self.product_uom_qty

