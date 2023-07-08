from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        for rec in self:
            product_ids = rec.move_ids_without_package.mapped('product_id')
            if product_ids and rec.purchase_id and rec.purchase_id.order_line_production_order:
                for line in rec.purchase_id.order_line_production_order:
                    if line.product_id in product_ids:
                        for material_line in line.purchase_order_line_material_line_ids:
                            if material_line.product_id.detailed_type == "product":
                                material_line.production_line_price_unit = material_line.product_id.standard_price
        return super(StockPicking, self)._action_done()