from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def create_from_ui(self, orders, draft=False):
        return super(PosOrder, self.with_context(create_from_ui=True)).create_from_ui(orders, draft=False)