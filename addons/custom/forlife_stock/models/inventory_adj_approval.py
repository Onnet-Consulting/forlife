# -*- coding: utf-8 -*-from odoo import api, fields, models
from odoo import api, fields, models, _


class InventoryAdjustmentApproval(models.Model):
    _inherit = "stock.quant"

    inventory_approved = fields.Boolean(default=False)

    def action_submit_to_manager(self):
        self.inventory_approved = True

    def action_apply_inventory(self):
        self.inventory_approved = False
        res = super(InventoryAdjustmentApproval, self).action_apply_inventory()
        return res

    def action_set_inventory_quantity_to_zero(self):
        self.inventory_approved = False
        res = super(InventoryAdjustmentApproval, self).action_set_inventory_quantity_to_zero()
        return res

class StockInventoryAdjustmentName(models.TransientModel):
    _inherit = 'stock.inventory.adjustment.name'


    def action_apply(self):
        quants = self.quant_ids.filtered('inventory_approved')
        return quants.with_context(inventory_name=self.inventory_adjustment_name).action_apply_inventory()


