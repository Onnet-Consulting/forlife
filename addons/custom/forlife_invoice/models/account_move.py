from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        if not res.purchase_order_product_id or res.purchase_order_product_id[0].is_inter_company != False:
            return res
        for line in res.invoice_line_ids:
            if line.product_id:
                line._compute_account_id()
        return res

class AccountTax(models.Model):
    _inherit = 'account.tax.repartition.line'

    product_id = fields.Many2one('product.product', string='Sản phẩm')

class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        new_picking_id, pick_type_id = super(StockReturnPicking, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        if self.picking_id:
            for item in new_picking:
                item.write({
                    'x_is_check_return': True,
                    'origin': self.picking_id.origin,
                    'relation_return': self.picking_id.name
                })
            for item in self.picking_id.move_line_ids_without_package:
                for line in new_picking.move_line_ids_without_package:
                    if item.product_id == line.product_id:
                        line.write({
                            'po_id': item.po_id
                        })
        return new_picking_id, pick_type_id



