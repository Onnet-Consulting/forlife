from odoo import _, api, fields, models


class Product(models.Model):
    _inherit = "product.product"

    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state')
    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'location', 'warehouse',
    )
    def _compute_quantities(self):
        context = self.env.context
        if context.get("create_from_ui", False) or context.get('job_uuid', False): 
            for product in self:
                product.qty_available = 0.0
                product.incoming_qty = 0.0
                product.outgoing_qty = 0.0
                product.virtual_available = 0.0
                product.free_qty = 0.0
        else:
            super(Product, self)._compute_quantities()
